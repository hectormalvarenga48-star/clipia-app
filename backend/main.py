from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField, Session, SQLModel, create_engine, select

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'clipia.db'}"
engine = create_engine(DATABASE_URL, echo=False)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
META_APP_ID = os.getenv("META_APP_ID", "")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "http://localhost:8000/auth/meta/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title="ClipIA Unified API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Video(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    title: str
    idea: str
    goal: str = "Educativo"
    hook: str
    script: str
    caption: str
    voice: str = "Español neutro"
    template: str = "Educativo dinámico"
    duration: int = 30
    format: str = "9:16"
    status: str = "Programado"
    platforms: str = "YouTube,Instagram,TikTok"
    scheduled_at: Optional[datetime] = None
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class VideoCreate(BaseModel):
    idea: str = Field(min_length=5)
    goal: str = "Educativo"
    voice: str = "Español neutro"
    template: str = "Educativo dinámico"
    platforms: List[str] = Field(default_factory=lambda: ["YouTube", "Instagram", "TikTok"])
    scheduled_at: Optional[datetime] = None


class VideoResponse(BaseModel):
    id: int
    title: str
    idea: str
    goal: str
    hook: str
    script: str
    caption: str
    voice: str
    template: str
    duration: int
    format: str
    status: str
    platforms: List[str]
    scheduled_at: Optional[datetime]
    created_at: datetime


class NetworkState(BaseModel):
    youtube: bool = False
    instagram: bool = False
    facebook: bool = False
    tiktok: bool = False


NETWORKS = NetworkState()


class PublishRequest(BaseModel):
    video_id: int
    platform: str
    video_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class OAuthStatus(BaseModel):
    google_configured: bool
    meta_configured: bool
    networks: NetworkState


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "clipia-unified-api"}


@app.get("/oauth/status", response_model=OAuthStatus)
def oauth_status() -> OAuthStatus:
    return OAuthStatus(
        google_configured=bool(GOOGLE_CLIENT_ID),
        meta_configured=bool(META_APP_ID),
        networks=NETWORKS,
    )


@app.get("/auth/google/start")
def auth_google_start() -> dict:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Falta GOOGLE_CLIENT_ID en .env")
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/userinfo.email",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return {"auth_url": url}


@app.get("/auth/meta/start")
def auth_meta_start() -> dict:
    if not META_APP_ID:
        raise HTTPException(status_code=400, detail="Falta META_APP_ID en .env")
    params = {
        "client_id": META_APP_ID,
        "redirect_uri": META_REDIRECT_URI,
        "response_type": "code",
        "scope": "instagram_basic,pages_show_list,instagram_content_publish,business_management,pages_read_engagement",
    }
    url = f"https://www.facebook.com/v23.0/dialog/oauth?{urlencode(params)}"
    return {"auth_url": url}


@app.get("/auth/google/callback")
def auth_google_callback(code: str) -> dict:
    # En producción: intercambiar 'code' por tokens y almacenarlos cifrados por usuario.
    global NETWORKS
    NETWORKS.youtube = True
    return {"ok": True, "message": "Google conectado en modo demo. Implementa el intercambio de token en producción.", "code_received": bool(code)}


@app.get("/auth/meta/callback")
def auth_meta_callback(code: str) -> dict:
    global NETWORKS
    NETWORKS.instagram = True
    NETWORKS.facebook = True
    return {"ok": True, "message": "Meta conectado en modo demo. Implementa el intercambio de token en producción.", "code_received": bool(code)}


@app.get("/videos", response_model=List[VideoResponse])
def list_videos() -> List[VideoResponse]:
    with Session(engine) as session:
        items = session.exec(select(Video).order_by(Video.created_at.desc())).all()
        return [to_response(item) for item in items]


@app.post("/videos/generate", response_model=VideoResponse, status_code=201)
def generate_video(payload: VideoCreate) -> VideoResponse:
    hook, script, caption = generate_copy(payload.idea, payload.goal)
    title = payload.idea[:60].strip().rstrip(".")
    video = Video(
        title=title,
        idea=payload.idea,
        goal=payload.goal,
        hook=hook,
        script=script,
        caption=caption,
        voice=payload.voice,
        template=payload.template,
        platforms=",".join(payload.platforms),
        scheduled_at=payload.scheduled_at,
    )
    with Session(engine) as session:
        session.add(video)
        session.commit()
        session.refresh(video)
        return to_response(video)


@app.delete("/videos/{video_id}")
def delete_video(video_id: int) -> dict:
    with Session(engine) as session:
        item = session.get(Video, video_id)
        if not item:
            raise HTTPException(status_code=404, detail="Video no encontrado")
        session.delete(item)
        session.commit()
        return {"ok": True}


@app.get("/stats")
def stats() -> dict:
    with Session(engine) as session:
        items = session.exec(select(Video)).all()
        return {
            "total_videos": len(items),
            "scheduled": len([v for v in items if v.status == "Programado"]),
            "published": len([v for v in items if v.status == "Publicado"]),
            "draft": len([v for v in items if v.status == "Borrador"]),
        }


@app.post("/publish")
def publish_video(payload: PublishRequest) -> dict:
    with Session(engine) as session:
        item = session.get(Video, payload.video_id)
        if not item:
            raise HTTPException(status_code=404, detail="Video no encontrado")

        platform = payload.platform.lower()
        if platform == "youtube":
            if not NETWORKS.youtube:
                raise HTTPException(status_code=400, detail="YouTube no está conectado todavía")
            item.status = "Publicado"
            session.add(item)
            session.commit()
            return {
                "ok": True,
                "message": "YouTube listo en modo demo. Sustituye este punto por youtube.videos.insert usando el access token del usuario.",
                "platform": "YouTube",
                "video_id": item.id,
            }

        if platform in {"instagram", "facebook"}:
            if not (NETWORKS.instagram or NETWORKS.facebook):
                raise HTTPException(status_code=400, detail="Meta no está conectado todavía")
            if not payload.video_url:
                raise HTTPException(status_code=400, detail="Para Instagram/Facebook en este MVP debes enviar video_url pública")
            item.status = "Publicado"
            session.add(item)
            session.commit()
            return {
                "ok": True,
                "message": f"{payload.platform} listo en modo demo. Sustituye este punto por /media + /media_publish de Meta.",
                "platform": payload.platform,
                "video_url": payload.video_url,
                "video_id": item.id,
            }

        if platform == "tiktok":
            if not NETWORKS.tiktok:
                raise HTTPException(status_code=400, detail="TikTok no está conectado todavía")
            item.status = "Publicado"
            session.add(item)
            session.commit()
            return {
                "ok": True,
                "message": "TikTok listo en modo demo. Sustituye este punto por la Content Posting API.",
                "platform": "TikTok",
                "video_id": item.id,
            }

        raise HTTPException(status_code=400, detail="Plataforma no soportada")


@app.get("/networks", response_model=NetworkState)
def get_networks() -> NetworkState:
    return NETWORKS


@app.put("/networks/{network}")
def toggle_network(network: str) -> NetworkState:
    global NETWORKS
    if not hasattr(NETWORKS, network):
        raise HTTPException(status_code=404, detail="Red no encontrada")
    current = getattr(NETWORKS, network)
    setattr(NETWORKS, network, not current)
    return NETWORKS


@app.get("/queue")
def queue_preview() -> dict:
    with Session(engine) as session:
        items = session.exec(select(Video).where(Video.status == "Programado")).all()
        return {
            "pending": len(items),
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "scheduled_at": item.scheduled_at,
                    "platforms": item.platforms.split(",") if item.platforms else [],
                }
                for item in items
            ],
        }


def generate_copy(idea: str, goal: str) -> tuple[str, str, str]:
    goal_normalized = goal.lower()
    if goal_normalized == "ventas":
        hook = "Si tu contenido no convierte, probablemente no necesitas publicar más: necesitas una mejor estructura."
        script = (
            f"Hoy te explico esta idea: {idea}. "
            "Cuando tu video abre con un beneficio claro, desarrolla una sola promesa fuerte y cierra con un llamado simple, aumentas la posibilidad de convertir atención en acción."
        )
    elif goal_normalized == "marca personal":
        hook = "Tu marca personal no crece por presencia: crece por claridad y repetición estratégica."
        script = (
            f"Partimos de esta idea: {idea}. "
            "El video debe sonar humano, directo y reconocible, para reforzar tu posicionamiento en cada publicación corta."
        )
    elif goal_normalized == "viral":
        hook = "La mayoría intenta volverse viral por accidente. El crecimiento mejora cuando el mensaje está diseñado para retener."
        script = (
            f"Tomamos esta idea: {idea}. "
            "La convertimos en un short con gancho rápido, desarrollo breve y una estructura muy fácil de consumir en menos de treinta segundos."
        )
    else:
        hook = "Hay una forma más simple de convertir una idea en contenido corto que sí conecte."
        script = (
            f"Partimos de esta idea: {idea}. "
            "La sintetizamos en un formato breve, vertical y claro para que pueda usarse en reels y shorts sin perder fuerza en el mensaje."
        )
    caption = f"Contenido generado con ClipIA para objetivo {goal.lower()}. #IA #Contenido #Reels #Shorts"
    return hook, script, caption


def to_response(item: Video) -> VideoResponse:
    return VideoResponse(
        id=item.id or 0,
        title=item.title,
        idea=item.idea,
        goal=item.goal,
        hook=item.hook,
        script=item.script,
        caption=item.caption,
        voice=item.voice,
        template=item.template,
        duration=item.duration,
        format=item.format,
        status=item.status,
        platforms=item.platforms.split(",") if item.platforms else [],
        scheduled_at=item.scheduled_at,
        created_at=item.created_at,
    )
