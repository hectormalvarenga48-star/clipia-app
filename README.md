# ClipIA unified app

Proyecto fullstack en español para crear videos cortos desde ideas, ver biblioteca, programar salidas y preparar publicación con flujos OAuth base para YouTube y Meta.

## Qué hace hoy
- Frontend React con panel unificado
- Backend FastAPI
- SQLite local
- Genera videos desde idea o texto
- Guarda biblioteca
- Estadísticas
- Inicio de OAuth para Google/YouTube y Meta
- Publicación en modo demo desde un solo panel

## Qué falta para producción real
- Intercambio real de tokens OAuth y almacenamiento cifrado por usuario
- Login real
- Cuentas multiusuario
- Subida/render real de video
- YouTube `videos.insert`
- Meta `/media` + `/media_publish`
- TikTok Content Posting API
- Cola asíncrona y workers

## Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # En Windows usa .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --port 8000
```

## Frontend
```bash
cd frontend
npm install
npm run dev
```

## URLs
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Docs API: http://localhost:8000/docs

## Variables de entorno
Completa `backend/.env` con tus credenciales reales de Google y Meta.

## Importante
Este proyecto sí une creación + biblioteca + preparación de OAuth + panel único.
No queda publicando “100% real” hasta que pongas credenciales, completes permisos y reemplaces los callbacks demo por el intercambio real de tokens.
