import { useState, useEffect, useCallback } from 'react'
import { api } from './api'
import type { Place, QueueStatus, SearchResult } from './types'

type ActionStatus = { type: 'idle' | 'loading' | 'success' | 'error'; message?: string }

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="text-yellow-500 text-sm">
      {'★'.repeat(Math.round(rating))}{'☆'.repeat(5 - Math.round(rating))}
      <span className="text-gray-500 ml-1">{rating.toFixed(1)}</span>
    </span>
  )
}

function StatusBadge({ published }: { published: boolean }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${published ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
      {published ? 'Publicado' : 'Pendiente'}
    </span>
  )
}

const incompleteLabels = {
  contact: 'Sin contacto',
  location: 'Ubicación incompleta',
  images: 'Sin imágenes',
  food_type: 'Sin tipo de comida',
  wordpress_link: 'Sin artículo en WordPress',
} as const

function ActionButton({
  label,
  status,
  onClick,
  variant = 'default',
}: {
  label: string
  status: ActionStatus
  onClick: () => void
  variant?: 'default' | 'primary' | 'pipeline'
}) {
  const base = 'w-full min-h-12 px-4 py-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 disabled:opacity-60'
  const variants = {
    default: 'bg-gray-100 hover:bg-gray-200 text-gray-800',
    primary: 'bg-green-700 hover:bg-green-800 text-white',
    pipeline: 'bg-green-900 hover:bg-green-950 text-white font-bold',
  }
  return (
    <div>
      <button
        onClick={onClick}
        disabled={status.type === 'loading'}
        className={`${base} ${variants[variant]}`}
      >
        {status.type === 'loading' && (
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {label}
      </button>
      {status.message && (
        <p className={`text-xs mt-1 px-1 ${status.type === 'error' ? 'text-red-600' : 'text-green-700'}`}>
          {status.message}
        </p>
      )}
    </div>
  )
}

function PlacePanel({ place, onRefresh }: { place: Place; onRefresh: () => void }) {
  const [reviewsStatus, setReviewsStatus] = useState<ActionStatus>({ type: 'idle' })
  const [articleStatus, setArticleStatus] = useState<ActionStatus>({ type: 'idle' })
  const [imagesStatus, setImagesStatus] = useState<ActionStatus>({ type: 'idle' })
  const [publishStatus, setPublishStatus] = useState<ActionStatus>({ type: 'idle' })
  const [pipelineStatus, setPipelineStatus] = useState<ActionStatus>({ type: 'idle' })
  const [enrichStatus, setEnrichStatus] = useState<ActionStatus>({ type: 'idle' })
  const [articleContent, setArticleContent] = useState<string | null>(null)
  const [showArticle, setShowArticle] = useState(false)

  const getReviews = useCallback(async () => {
    setReviewsStatus({ type: 'loading' })
    try {
      const res = await api.reviews(place.place_id)
      setReviewsStatus({ type: 'success', message: res.message })
    } catch (e) {
      setReviewsStatus({ type: 'error', message: String(e) })
    }
  }, [place.place_id])

  const generateArticle = useCallback(async () => {
    setArticleStatus({ type: 'loading' })
    try {
      const res = await api.generateArticle(place.place_id)
      setArticleContent(res.content)
      setArticleStatus({ type: 'success', message: 'Artículo generado ✓' })
    } catch (e) {
      setArticleStatus({ type: 'error', message: String(e) })
    }
  }, [place.place_id])

  const downloadImages = useCallback(async () => {
    setImagesStatus({ type: 'loading' })
    try {
      const res = await api.downloadImages(place.place_id)
      await api.setFeaturedRandom(place.place_id)
      setImagesStatus({ type: 'success', message: res.message })
    } catch (e) {
      setImagesStatus({ type: 'error', message: String(e) })
    }
  }, [place.place_id])

  const publish = useCallback(async () => {
    setPublishStatus({ type: 'loading' })
    try {
      const res = await api.publish(place.place_id)
      setPublishStatus({ type: 'success', message: `${res.message} (ID: ${res.post_id})` })
      onRefresh()
    } catch (e) {
      setPublishStatus({ type: 'error', message: String(e) })
    }
  }, [place.place_id, onRefresh])

  const runPipeline = useCallback(async () => {
    setPipelineStatus({ type: 'loading', message: 'Obteniendo reseñas...' })
    try {
      await api.reviews(place.place_id)
      setPipelineStatus({ type: 'loading', message: 'Generando artículo...' })
      const articleRes = await api.generateArticle(place.place_id)
      setArticleContent(articleRes.content)
      setPipelineStatus({ type: 'loading', message: 'Descargando imágenes...' })
      await api.downloadImages(place.place_id)
      await api.setFeaturedRandom(place.place_id)
      setPipelineStatus({ type: 'loading', message: 'Publicando en WordPress...' })
      const pubRes = await api.publish(place.place_id)
      setPipelineStatus({ type: 'success', message: `¡Publicado! Post ID: ${pubRes.post_id}` })
      onRefresh()
    } catch (e) {
      setPipelineStatus({ type: 'error', message: String(e) })
    }
  }, [place.place_id, onRefresh])

  const enrichPlace = useCallback(async () => {
    setEnrichStatus({ type: 'loading' })
    try {
      const result = await api.enrichPlace(place.place_id)
      setEnrichStatus({
        type: 'success',
        message: result.wordpress_synced
          ? 'Datos y WordPress actualizados ✓'
          : 'Datos locales actualizados ✓',
      })
      onRefresh()
    } catch (e) {
      setEnrichStatus({
        type: 'error',
        message: e instanceof Error ? e.message : String(e),
      })
    }
  }, [place.place_id, onRefresh])

  return (
    <div className="bg-gray-50 border-t border-gray-200 p-4 space-y-3">
      {place.phone && <p className="text-sm text-gray-600">📞 {place.phone}</p>}
      {place.website && (
        <a href={place.website} target="_blank" rel="noopener noreferrer" className="text-sm text-green-700 underline block truncate">
          🌐 {place.website}
        </a>
      )}

      <div className="grid grid-cols-1 gap-2">
        {(place.incomplete_fields?.includes('location') || place.incomplete_fields?.includes('contact')) && (
          <ActionButton
            label="Actualizar datos desde Google"
            status={enrichStatus}
            onClick={enrichPlace}
          />
        )}
        <ActionButton label="1. Obtener reseñas" status={reviewsStatus} onClick={getReviews} />
        <ActionButton label="2. Generar artículo" status={articleStatus} onClick={generateArticle} />
        {articleContent && (
          <button
            onClick={() => setShowArticle(!showArticle)}
            className="text-xs text-green-700 underline text-left px-1"
          >
            {showArticle ? 'Ocultar artículo' : 'Ver artículo generado'}
          </button>
        )}
        {showArticle && articleContent && (
          <div className="bg-white border border-gray-200 rounded-lg p-3 max-h-64 overflow-y-auto text-xs text-gray-700 whitespace-pre-wrap font-mono">
            {articleContent}
          </div>
        )}
        <ActionButton label="3. Descargar imágenes" status={imagesStatus} onClick={downloadImages} />
        {(!place.publicado_en_wp || !place.article_path) && (
          <>
            <ActionButton
              label={place.publicado_en_wp ? '4. Volver a publicar en WordPress' : '4. Publicar en WordPress'}
              status={publishStatus}
              onClick={publish}
              variant="primary"
            />
            <div className="border-t border-gray-200 pt-2">
              <ActionButton
                label={place.publicado_en_wp
                  ? '🚀 Pipeline completo: reparar y volver a publicar'
                  : '🚀 Pipeline completo (1→2→3→4)'}
                status={pipelineStatus}
                onClick={runPipeline}
                variant="pipeline"
              />
            </div>
          </>
        )}
        {place.publicado_en_wp && place.article_path && (
          <a
            href={place.article_path}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full min-h-12 px-4 py-3 rounded-lg text-sm font-medium bg-green-100 hover:bg-green-200 text-green-800 flex items-center justify-center gap-2"
          >
            Ver artículo en WordPress ↗
          </a>
        )}
      </div>
    </div>
  )
}

function PlaceCard({ place, onRefresh }: { place: Place; onRefresh: () => void }) {
  const [expanded, setExpanded] = useState(false)

  const [deleteStatus, setDeleteStatus] = useState<ActionStatus>({ type: 'idle' })

  const handleDelete = useCallback(async () => {
    setDeleteStatus({ type: 'loading' })
    try {
      await api.deletePlace(place.place_id)
      setDeleteStatus({ type: 'success' })
      onRefresh()
    } catch (e) {
      setDeleteStatus({ type: 'error', message: e instanceof Error ? e.message : String(e) })
    }
  }, [place.place_id, onRefresh])

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="flex items-stretch">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex-1 min-w-0 text-left p-4 flex items-start justify-between gap-3"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-gray-900 text-sm">{place.name}</h3>
              <StatusBadge published={!!place.publicado_en_wp} />
            </div>
            <p className="text-xs text-gray-500 mt-0.5 truncate">{place.address}</p>
            {(place.city || place.postal_code) && (
              <p className="text-[11px] text-gray-500 mt-0.5">
                {[place.city, place.postal_code].filter(Boolean).join(' · ')}
              </p>
            )}
            <div className="flex items-center gap-2 mt-1">
              <StarRating rating={place.rating} />
              {place.tipo_de_comida && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{place.tipo_de_comida}</span>
              )}
            </div>
            {!!place.incomplete_fields?.length && (
              <div className="flex flex-wrap gap-1 mt-2">
                {place.incomplete_fields.map(field => (
                  <span key={field} className="text-[10px] bg-red-50 text-red-700 px-2 py-0.5 rounded-full">
                    {incompleteLabels[field]}
                  </span>
                ))}
              </div>
            )}
          </div>
          <span className="text-gray-400 text-lg mt-0.5">{expanded ? '▲' : '▼'}</span>
        </button>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleteStatus.type === 'loading'}
          aria-label={`Eliminar ${place.name}`}
          title="Eliminar definitivamente"
          className="w-12 shrink-0 border-l border-gray-100 text-red-500 hover:text-white hover:bg-red-600 transition-colors flex items-center justify-center disabled:opacity-50"
        >
          {deleteStatus.type === 'loading'
            ? <span className="w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
            : <span className="text-xl font-bold" aria-hidden="true">×</span>}
        </button>
      </div>
      {deleteStatus.type === 'error' && (
        <p className="text-xs text-red-600 bg-red-50 border-t border-red-100 px-4 py-2">{deleteStatus.message}</p>
      )}
      {expanded && <PlacePanel place={place} onRefresh={onRefresh} />}
    </div>
  )
}

function SearchResultCard({ result, saved, onSaved }: { result: SearchResult; saved: boolean; onSaved: (placeId: string) => void }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async () => {
    if (saved) return
    setSaving(true)
    setError('')
    try {
      await api.savePlace(result.place_id)
      onSaved(result.place_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start justify-between gap-3">
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-gray-900 text-sm">{result.name}</h3>
        <p className="text-xs text-gray-500 mt-0.5 truncate">{result.address}</p>
        {(result.city || result.postal_code) && (
          <p className="text-[11px] text-blue-700 mt-0.5">
            {[result.city, result.district, result.postal_code].filter(Boolean).join(' · ')}
          </p>
        )}
        <StarRating rating={result.rating} />
      </div>
      <div className="shrink-0 text-right">
        <button
          onClick={handleSave}
          disabled={saving || saved}
          className={`text-xs px-3 py-2 rounded-lg flex items-center gap-1 ${saved ? 'bg-green-100 text-green-800' : 'bg-blue-600 hover:bg-blue-700 text-white'} disabled:opacity-70`}
        >
          {saving && <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />}
          {saved ? 'Guardado ✓' : 'Guardar'}
        </button>
        {error && <p className="text-[10px] text-red-600 mt-1 max-w-32">{error}</p>}
      </div>
    </div>
  )
}

function LoginScreen({ onLogin }: { onLogin: (username: string) => void }) {
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const result = await api.login('enguillem', password)
      onLogin(result.username)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se ha podido iniciar sesión')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm bg-white rounded-2xl shadow-lg border border-gray-200 p-6">
        <div className="text-center mb-6">
          <div className="text-4xl mb-2">🗺️</div>
          <h1 className="text-xl font-bold text-gray-900">AI Maps Manager</h1>
          <p className="text-sm text-gray-500 mt-1">Acceso para enguillem</p>
        </div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          autoComplete="current-password"
          autoFocus
          required
          className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-green-700"
        />
        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        <button
          type="submit"
          disabled={loading || !password}
          className="w-full mt-4 min-h-12 rounded-lg bg-green-800 hover:bg-green-900 text-white text-sm font-semibold disabled:opacity-60 flex items-center justify-center gap-2"
        >
          {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
          Entrar
        </button>
      </form>
    </main>
  )
}

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.ceil((seconds % 3600) / 60)
  return hours ? `${hours} h ${minutes} min` : `${minutes} min`
}

function QueuePanel({ status, busy, error, onAction, title, description, allLabel }: {
  status: QueueStatus | null
  busy: boolean
  error: string
  onAction: (action: 'test' | 'all' | 'pause' | 'resume' | 'retry') => void
  title?: string
  description?: string
  allLabel?: string
}) {
  if (!status) return null
  const remaining = status.pending + status.processing
  const nextRun = status.next_run_at
    ? new Date(status.next_run_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null

  return (
    <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-gray-900 text-sm">{title || 'Publicación automática'}</h2>
          <p className="text-xs text-gray-500 mt-0.5">{description || 'Un restaurante cada 5 minutos · máximo 3 intentos'}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${status.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
          {status.active ? 'Activa' : 'Pausada'}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-2 text-center">
        <div className="bg-yellow-50 rounded-lg p-2"><div className="font-bold">{status.pending}</div><div className="text-[10px] text-gray-500">En cola</div></div>
        <div className="bg-blue-50 rounded-lg p-2"><div className="font-bold">{status.processing}</div><div className="text-[10px] text-gray-500">Procesando</div></div>
        <div className="bg-green-50 rounded-lg p-2"><div className="font-bold">{status.completed}</div><div className="text-[10px] text-gray-500">Terminados</div></div>
        <div className="bg-red-50 rounded-lg p-2"><div className="font-bold">{status.failed}</div><div className="text-[10px] text-gray-500">Errores</div></div>
      </div>

      {status.current && (
        <p className="text-xs bg-blue-50 text-blue-800 rounded-lg px-3 py-2">
          Procesando: <strong>{status.current.name || status.current.place_id}</strong> · intento {status.current.attempts}/3
        </p>
      )}
      {remaining > 0 && (
        <p className="text-xs text-gray-600">
          Tiempo estimado: <strong>{formatDuration(status.estimated_seconds)}</strong>
          {nextRun && <> · Próxima ejecución: <strong>{nextRun}</strong></>}
        </p>
      )}

      <div className="grid grid-cols-2 gap-2">
        {status.total === 0 && (
          <button disabled={busy} onClick={() => onAction('test')} className="col-span-2 min-h-11 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold disabled:opacity-60">
            Probar con 3 restaurantes
          </button>
        )}
        {(status.total > 0 || !!allLabel) && (
          <button disabled={busy} onClick={() => onAction('all')} className="min-h-11 rounded-lg bg-green-800 hover:bg-green-900 text-white text-sm font-semibold disabled:opacity-60">
            {allLabel || 'Añadir todos los pendientes'}
          </button>
        )}
        {status.active ? (
          <button disabled={busy} onClick={() => onAction('pause')} className="min-h-11 rounded-lg bg-gray-200 hover:bg-gray-300 text-gray-800 text-sm font-semibold disabled:opacity-60">
            Pausar
          </button>
        ) : remaining > 0 ? (
          <button disabled={busy} onClick={() => onAction('resume')} className="min-h-11 rounded-lg bg-green-700 hover:bg-green-800 text-white text-sm font-semibold disabled:opacity-60">
            Reanudar
          </button>
        ) : null}
        {status.failed > 0 && (
          <button disabled={busy} onClick={() => onAction('retry')} className="col-span-2 min-h-10 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 text-sm font-medium disabled:opacity-60">
            Reintentar errores
          </button>
        )}
      </div>
      {busy && <p className="text-xs text-blue-700">Actualizando cola...</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
      {status.recent_errors.length > 0 && (
        <details className="text-xs">
          <summary className="text-red-700 cursor-pointer">Ver errores recientes</summary>
          <div className="mt-2 space-y-2">
            {status.recent_errors.map(item => (
              <div key={item.place_id} className="bg-red-50 rounded p-2">
                <strong>{item.name || item.place_id}</strong>: {item.last_error}
              </div>
            ))}
          </div>
        </details>
      )}
    </section>
  )
}

function Dashboard({ username, onLogout }: { username: string; onLogout: () => void }) {
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [places, setPlaces] = useState<Place[]>([])
  const [loadingPlaces, setLoadingPlaces] = useState(true)
  const [activeFilter, setActiveFilter] = useState<'all' | 'pending' | 'published' | 'incomplete'>('all')
  const [maximumRating, setMaximumRating] = useState<string>('')
  const [incompleteField, setIncompleteField] = useState<string>('')
  const [savedPlaceIds, setSavedPlaceIds] = useState<Set<string>>(new Set())
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [queueBusy, setQueueBusy] = useState(false)
  const [queueError, setQueueError] = useState('')
  const [repairQueueStatus, setRepairQueueStatus] = useState<QueueStatus | null>(null)
  const [repairQueueBusy, setRepairQueueBusy] = useState(false)
  const [repairQueueError, setRepairQueueError] = useState('')

  const loadPlaces = useCallback(async () => {
    try {
      const res = await api.saved()
      setPlaces(res.guardats)
      setSavedPlaceIds(new Set(res.guardats.map(place => place.place_id)))
    } finally {
      setLoadingPlaces(false)
    }
  }, [])

  useEffect(() => { loadPlaces() }, [loadPlaces])

  const loadQueue = useCallback(async () => {
    try {
      setQueueStatus(await api.queueStatus())
    } catch (e) {
      setQueueError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  const loadRepairQueue = useCallback(async () => {
    try {
      setRepairQueueStatus(await api.repairQueueStatus())
    } catch (e) {
      setRepairQueueError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  useEffect(() => {
    loadQueue()
    loadRepairQueue()
    const timer = window.setInterval(() => {
      loadQueue()
      loadRepairQueue()
      loadPlaces()
    }, 10000)
    return () => window.clearInterval(timer)
  }, [loadQueue, loadRepairQueue, loadPlaces])

  const queueAction = async (action: 'test' | 'all' | 'pause' | 'resume' | 'retry') => {
    setQueueBusy(true)
    setQueueError('')
    try {
      const result = action === 'test' ? await api.startQueue(3)
        : action === 'all' ? await api.startQueue(500)
        : action === 'pause' ? await api.pauseQueue()
        : action === 'resume' ? await api.resumeQueue()
        : await api.retryFailedQueue()
      setQueueStatus(result)
    } catch (e) {
      setQueueError(e instanceof Error ? e.message : String(e))
    } finally {
      setQueueBusy(false)
    }
  }

  const repairQueueAction = async (action: 'test' | 'all' | 'pause' | 'resume' | 'retry') => {
    setRepairQueueBusy(true)
    setRepairQueueError('')
    try {
      const result = action === 'test' ? await api.startRepairQueue(3)
        : action === 'all' ? await api.startRepairQueue(500)
        : action === 'pause' ? await api.pauseRepairQueue()
        : action === 'resume' ? await api.resumeRepairQueue()
        : await api.retryFailedRepairQueue()
      setRepairQueueStatus(result)
    } catch (e) {
      setRepairQueueError(e instanceof Error ? e.message : String(e))
    } finally {
      setRepairQueueBusy(false)
    }
  }

  const handleGoogleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    setSearchResults([])
    try {
      const res = await api.search(query)
      setSearchResults(res.resultados)
    } finally {
      setSearching(false)
    }
  }

  const filteredPlaces = places.filter(p => {
    const matchesFilter =
      activeFilter === 'all' ? true :
      activeFilter === 'pending' ? !p.publicado_en_wp :
      activeFilter === 'published' ? !!p.publicado_en_wp :
      !!p.is_incomplete
    const matchesQuery = !query.trim() || p.name.toLowerCase().includes(query.toLowerCase())
    const matchesRating = !maximumRating || p.rating < Number(maximumRating)
    const matchesIncompleteField =
      activeFilter !== 'incomplete' ||
      !incompleteField ||
      p.incomplete_fields?.includes(incompleteField as 'contact' | 'location' | 'images' | 'food_type' | 'wordpress_link')
    return matchesFilter && matchesQuery && matchesRating && matchesIncompleteField
  })

  const publishedCount = places.filter(p => p.publicado_en_wp).length
  const pendingCount = places.filter(p => !p.publicado_en_wp).length
  const incompleteCount = places.filter(p => p.is_incomplete).length

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-green-900 text-white px-4 py-5 sticky top-0 z-10 shadow-lg">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold">🗺️ AI Maps Manager</h1>
            <p className="text-green-300 text-xs mt-0.5">Gestor de restaurantes → dondecomerbien.com</p>
          </div>
          <button onClick={onLogout} className="text-xs text-green-200 hover:text-white whitespace-nowrap">
            {username} · Salir
          </button>
        </div>

        {/* Search bar */}
        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={query}
            onChange={e => { setQuery(e.target.value); setSearchResults([]) }}
            onKeyDown={e => e.key === 'Escape' && setQuery('')}
            placeholder="Filtrar lugares guardados..."
            className="flex-1 rounded-lg px-4 py-2.5 text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-green-400"
          />
          <button
            onClick={handleGoogleSearch}
            disabled={searching || !query.trim()}
            title="Buscar en Google Maps"
            className="bg-green-600 hover:bg-green-500 px-3 py-2.5 rounded-lg text-sm font-medium disabled:opacity-60 flex items-center gap-1 shrink-0"
          >
            {searching
              ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              : '+ Maps'}
          </button>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-4 space-y-4">
        {/* Search results */}
        {searchResults.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Resultados de búsqueda ({searchResults.length})
            </h2>
            <div className="space-y-2">
              {searchResults.map(r => (
                <SearchResultCard
                  key={r.place_id}
                  result={r}
                  saved={savedPlaceIds.has(r.place_id)}
                  onSaved={placeId => {
                    setSavedPlaceIds(previous => new Set(previous).add(placeId))
                    loadPlaces()
                  }}
                />
              ))}
            </div>
          </section>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {[
            { label: 'Total', count: places.length, key: 'all' as const, color: 'bg-white' },
            { label: 'Pendientes', count: pendingCount, key: 'pending' as const, color: 'bg-yellow-50' },
            { label: 'Publicados', count: publishedCount, key: 'published' as const, color: 'bg-green-50' },
            { label: 'Incompletos', count: incompleteCount, key: 'incomplete' as const, color: 'bg-red-50' },
          ].map(({ label, count, key, color }) => (
            <button
              key={key}
              onClick={() => setActiveFilter(key)}
              className={`${color} rounded-xl p-3 text-center shadow-sm border-2 transition-all ${activeFilter === key ? 'border-green-600' : 'border-transparent'}`}
            >
              <div className="text-2xl font-bold text-gray-900">{count}</div>
              <div className="text-xs text-gray-500">{label}</div>
            </button>
          ))}
        </div>

        {activeFilter === 'incomplete' && (
          <div className="bg-white rounded-xl shadow-sm border border-red-100 p-3 flex items-center gap-3">
            <label htmlFor="incomplete-filter" className="text-sm font-medium text-gray-700 whitespace-nowrap">
              Falta
            </label>
            <select
              id="incomplete-filter"
              value={incompleteField}
              onChange={event => setIncompleteField(event.target.value)}
              className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-red-600"
            >
              <option value="">Cualquier dato</option>
              <option value="contact">Contacto</option>
              <option value="location">Ubicación completa</option>
              <option value="images">Imágenes</option>
              <option value="food_type">Tipo de comida</option>
              <option value="wordpress_link">Artículo en WordPress</option>
            </select>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {filteredPlaces.length} resultados
            </span>
          </div>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-3 flex items-center gap-3">
          <label htmlFor="rating-filter" className="text-sm font-medium text-gray-700 whitespace-nowrap">
            Puntuación
          </label>
          <select
            id="rating-filter"
            value={maximumRating}
            onChange={event => setMaximumRating(event.target.value)}
            className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-green-700"
          >
            <option value="">Cualquier puntuación</option>
            <option value="4.5">Menos de 4,5</option>
            <option value="4">Menos de 4</option>
            <option value="3.5">Menos de 3,5</option>
            <option value="3">Menos de 3</option>
          </select>
          {maximumRating && (
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {filteredPlaces.length} resultados
            </span>
          )}
        </div>

        <QueuePanel status={queueStatus} busy={queueBusy} error={queueError} onAction={queueAction} />

        <QueuePanel
          status={repairQueueStatus}
          busy={repairQueueBusy}
          error={repairQueueError}
          onAction={repairQueueAction}
          title="Reparación automática"
          description="Una ficha incompleta cada 5 minutos · máximo 3 intentos"
          allLabel="Reparar todas las fichas incompletas"
        />

        {/* Places list */}
        <section>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            {activeFilter === 'all'
              ? 'Todos los lugares'
              : activeFilter === 'pending'
                ? 'Pendientes de publicar'
                : activeFilter === 'published'
                  ? 'Publicados'
                  : 'Datos incompletos'}
          </h2>
          {loadingPlaces ? (
            <div className="text-center py-12">
              <span className="w-8 h-8 border-4 border-green-700 border-t-transparent rounded-full animate-spin inline-block" />
            </div>
          ) : filteredPlaces.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <p className="text-4xl mb-2">🍽️</p>
              <p className="text-sm">No hay lugares guardados</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredPlaces.map(p => (
                <PlaceCard key={p.place_id} place={p} onRefresh={loadPlaces} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

export default function App() {
  const [username, setUsername] = useState<string | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    api.me()
      .then(result => setUsername(result.username))
      .catch(() => setUsername(null))
      .finally(() => setCheckingSession(false))
  }, [])

  const logout = async () => {
    try {
      await api.logout()
    } finally {
      setUsername(null)
    }
  }

  if (checkingSession) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <span className="w-8 h-8 border-4 border-green-700 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return username
    ? <Dashboard username={username} onLogout={logout} />
    : <LoginScreen onLogin={setUsername} />
}
