import React, { useEffect, useState } from 'react'

const API = 'http://localhost:8000'

function Card({ title, children }) {
  return (
    <div className="rounded-3xl border bg-white p-5 shadow-sm">
      <h2 className="text-xl font-bold tracking-tight">{title}</h2>
      <div className="mt-4">{children}</div>
    </div>
  )
}

export default function App() {
  const [stats, setStats] = useState({ total_videos: 0, scheduled: 0, published: 0, draft: 0 })
  const [videos, setVideos] = useState([])
  const [oauth, setOauth] = useState({ google_configured: false, meta_configured: false, networks: {} })
  const [form, setForm] = useState({
    idea: '',
    goal: 'Educativo',
    voice: 'Español neutro',
    template: 'Educativo dinámico',
    platforms: ['YouTube', 'Instagram', 'TikTok'],
    scheduled_at: ''
  })
  const [videoUrl, setVideoUrl] = useState('')
  const [message, setMessage] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState('YouTube')

  async function load() {
    const [statsRes, videosRes, oauthRes] = await Promise.all([
      fetch(`${API}/stats`).then(r => r.json()),
      fetch(`${API}/videos`).then(r => r.json()),
      fetch(`${API}/oauth/status`).then(r => r.json())
    ])
    setStats(statsRes)
    setVideos(videosRes)
    setOauth(oauthRes)
  }

  useEffect(() => { load() }, [])

  function togglePlatform(platform) {
    setForm(prev => ({
      ...prev,
      platforms: prev.platforms.includes(platform)
        ? prev.platforms.filter(p => p !== platform)
        : [...prev.platforms, platform]
    }))
  }

  async function createVideo(e) {
    e.preventDefault()
    setMessage('Generando video...')
    const res = await fetch(`${API}/videos/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        scheduled_at: form.scheduled_at || null
      })
    })
    const data = await res.json()
    if (!res.ok) {
      setMessage(data.detail || 'Error al generar')
      return
    }
    setMessage('Video generado correctamente')
    setForm({ ...form, idea: '' })
    load()
  }

  async function startAuth(type) {
    const res = await fetch(`${API}/auth/${type}/start`)
    const data = await res.json()
    if (!res.ok) {
      setMessage(data.detail || 'No se pudo iniciar OAuth')
      return
    }
    window.open(data.auth_url, '_blank')
  }

  async function publish(videoId) {
    setMessage('Publicando...')
    const res = await fetch(`${API}/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: videoId,
        platform: selectedPlatform,
        video_url: ['Instagram', 'Facebook'].includes(selectedPlatform) ? videoUrl : null
      })
    })
    const data = await res.json()
    setMessage(data.message || data.detail || 'Sin respuesta')
    load()
  }

  async function deleteVideo(id) {
    await fetch(`${API}/videos/${id}`, { method: 'DELETE' })
    load()
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="rounded-3xl border bg-white p-6 shadow-sm">
          <h1 className="text-3xl font-bold tracking-tight">ClipIA</h1>
          <p className="mt-2 text-slate-600">App unificada para crear, programar y preparar publicación de shorts en español.</p>
          {message && <div className="mt-4 rounded-2xl bg-slate-100 px-4 py-3 text-sm">{message}</div>}
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {[
            ['Videos', stats.total_videos],
            ['Programados', stats.scheduled],
            ['Publicados', stats.published],
            ['Borradores', stats.draft]
          ].map(([label, value]) => (
            <div key={label} className="rounded-3xl border bg-white p-5 shadow-sm">
              <div className="text-sm text-slate-500">{label}</div>
              <div className="mt-2 text-3xl font-bold">{value}</div>
            </div>
          ))}
        </div>

        <div className="mt-6 grid gap-6 xl:grid-cols-2">
          <Card title="Crear video con IA">
            <form onSubmit={createVideo} className="space-y-4">
              <textarea
                className="w-full min-h-36 rounded-2xl border p-4"
                placeholder="Escribe la idea del reel o short"
                value={form.idea}
                onChange={e => setForm({ ...form, idea: e.target.value })}
              />
              <div className="grid gap-4 md:grid-cols-2">
                <select className="rounded-2xl border p-3" value={form.goal} onChange={e => setForm({ ...form, goal: e.target.value })}>
                  <option>Educativo</option>
                  <option>Ventas</option>
                  <option>Marca personal</option>
                  <option>Viral</option>
                </select>
                <input type="datetime-local" className="rounded-2xl border p-3" value={form.scheduled_at} onChange={e => setForm({ ...form, scheduled_at: e.target.value })} />
              </div>
              <div className="flex flex-wrap gap-2">
                {['YouTube', 'Instagram', 'Facebook', 'TikTok'].map(platform => (
                  <button
                    type="button"
                    key={platform}
                    onClick={() => togglePlatform(platform)}
                    className={`rounded-full border px-4 py-2 text-sm ${form.platforms.includes(platform) ? 'bg-slate-900 text-white border-slate-900' : 'bg-white'}`}
                  >
                    {platform}
                  </button>
                ))}
              </div>
              <button className="rounded-2xl bg-slate-900 px-5 py-3 text-white">Generar video</button>
            </form>
          </Card>

          <Card title="Conectar redes">
            <div className="space-y-4">
              <div className="text-sm text-slate-600">Google configurado: {oauth.google_configured ? 'Sí' : 'No'}</div>
              <div className="text-sm text-slate-600">Meta configurado: {oauth.meta_configured ? 'Sí' : 'No'}</div>
              <div className="flex flex-wrap gap-3">
                <button onClick={() => startAuth('google')} className="rounded-2xl border px-4 py-3">Conectar YouTube</button>
                <button onClick={() => startAuth('meta')} className="rounded-2xl border px-4 py-3">Conectar Instagram/Facebook</button>
              </div>
              <div className="rounded-2xl bg-slate-100 p-4 text-sm">
                En este proyecto, la conexión devuelve una URL OAuth real. El callback está en modo demo hasta que agregues el intercambio de token con tus credenciales.
              </div>
            </div>
          </Card>
        </div>

        <div className="mt-6">
          <Card title="Biblioteca y publicación">
            <div className="mb-4 grid gap-4 md:grid-cols-2">
              <select className="rounded-2xl border p-3" value={selectedPlatform} onChange={e => setSelectedPlatform(e.target.value)}>
                <option>YouTube</option>
                <option>Instagram</option>
                <option>Facebook</option>
                <option>TikTok</option>
              </select>
              <input className="rounded-2xl border p-3" placeholder="Video URL pública (solo Instagram/Facebook en este MVP)" value={videoUrl} onChange={e => setVideoUrl(e.target.value)} />
            </div>
            <div className="space-y-4">
              {videos.map(video => (
                <div key={video.id} className="rounded-3xl border bg-slate-50 p-4">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="text-lg font-bold">{video.title}</div>
                      <div className="mt-2 text-sm text-slate-600">{video.hook}</div>
                      <div className="mt-2 text-sm text-slate-500">Estado: {video.status}</div>
                      <div className="mt-1 text-sm text-slate-500">Plataformas: {video.platforms.join(', ')}</div>
                      <div className="mt-3 grid gap-3 md:grid-cols-2">
                        <div className="rounded-2xl bg-white p-3 text-sm"><strong>Guion:</strong> {video.script}</div>
                        <div className="rounded-2xl bg-white p-3 text-sm"><strong>Caption:</strong> {video.caption}</div>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => publish(video.id)} className="rounded-2xl bg-slate-900 px-4 py-3 text-white">Publicar</button>
                      <button onClick={() => deleteVideo(video.id)} className="rounded-2xl border px-4 py-3">Eliminar</button>
                    </div>
                  </div>
                </div>
              ))}
              {!videos.length && <div className="text-sm text-slate-500">Todavía no hay videos creados.</div>}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
