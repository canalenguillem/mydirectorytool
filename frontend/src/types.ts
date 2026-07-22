export interface Place {
  name: string
  address: string
  place_id: string
  rating: number
  postal_code?: string
  phone?: string
  website?: string
  publicado_en_wp?: number
  wp_post_id?: number
  article_path?: string
  tipo_de_comida?: string
}

export interface SearchResult {
  name: string
  address: string
  place_id: string
  rating: number
  postal_code?: string
  phone?: string
  website?: string
}

export interface QueueError {
  place_id: string
  name?: string
  attempts: number
  last_error: string
}

export interface QueueStatus {
  active: boolean
  interval_seconds: number
  next_run_at?: number
  pending: number
  processing: number
  completed: number
  failed: number
  total: number
  estimated_seconds: number
  current?: { place_id: string; name?: string; attempts: number }
  recent_errors: QueueError[]
  added?: number
  retried?: number
}
