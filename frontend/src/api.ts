const BASE = import.meta.env.VITE_API_URL ?? '/api'

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { ...options, credentials: 'include' })
  if (!res.ok) {
    const body = await res.json().catch(() => null) as { detail?: string } | null
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  login: (username: string, password: string) =>
    req<{ username: string }>('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),

  me: () => req<{ username: string }>('/auth/me'),

  logout: () => req<void>('/auth/logout', { method: 'POST' }),

  queueStatus: () =>
    req<import('./types').QueueStatus>('/queue/status'),

  startQueue: (limit: number, intervalSeconds = 300) =>
    req<import('./types').QueueStatus>(`/queue/start?limit=${limit}&interval_seconds=${intervalSeconds}`, { method: 'POST' }),

  pauseQueue: () =>
    req<import('./types').QueueStatus>('/queue/pause', { method: 'POST' }),

  resumeQueue: () =>
    req<import('./types').QueueStatus>('/queue/resume', { method: 'POST' }),

  retryFailedQueue: () =>
    req<import('./types').QueueStatus>('/queue/retry-failed', { method: 'POST' }),

  repairQueueStatus: () =>
    req<import('./types').QueueStatus>('/repair-queue/status'),

  startRepairQueue: (limit: number, intervalSeconds = 300) =>
    req<import('./types').QueueStatus>(`/repair-queue/start?limit=${limit}&interval_seconds=${intervalSeconds}`, { method: 'POST' }),

  pauseRepairQueue: () =>
    req<import('./types').QueueStatus>('/repair-queue/pause', { method: 'POST' }),

  resumeRepairQueue: () =>
    req<import('./types').QueueStatus>('/repair-queue/resume', { method: 'POST' }),

  retryFailedRepairQueue: () =>
    req<import('./types').QueueStatus>('/repair-queue/retry-failed', { method: 'POST' }),

  search: (query: string) =>
    req<{ resultados: import('./types').SearchResult[] }>(`/places/search?query=${encodeURIComponent(query)}`),

  saved: () =>
    req<{ guardats: import('./types').Place[] }>('/places/saved'),

  enrichPlace: (place_id: string) =>
    req<{
      message: string
      wordpress_synced: boolean
      place: import('./types').Place
    }>(`/places/enrich?place_id=${encodeURIComponent(place_id)}`, { method: 'POST' }),

  savePlace: (place_id: string) =>
    req<{ message: string; place: import('./types').Place }>(`/places/save?place_id=${encodeURIComponent(place_id)}`, { method: 'POST' }),

  reviews: (place_id: string) =>
    req<{ message: string }>(`/places/reviews?place_id=${place_id}`),

  generateArticle: (place_id: string, lang = 'es') =>
    req<{ title: string; content: string }>('/places/blog', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ place_id, lang }),
    }),

  downloadImages: (place_id: string) =>
    req<{ message: string; imagenes: string[] }>(`/places/places/download-images?place_id=${place_id}`, { method: 'POST' }),

  setFeaturedRandom: (place_id: string) =>
    req<{ message: string }>(`/places/places/set-featured-random?place_id=${place_id}`, { method: 'POST' }),

  publish: (place_id: string) =>
    req<{ message: string; post_id: number }>(`/blog/blog/full-publish?place_id=${place_id}`, { method: 'POST' }),

  deletePlace: (place_id: string) =>
    req<{
      message: string
      wordpress_post_id?: number
      deleted_media: number[]
      deleted_local_files: number
    }>(`/places/places/delete?place_id=${encodeURIComponent(place_id)}`, { method: 'DELETE' }),
}
