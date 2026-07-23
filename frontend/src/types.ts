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
  country?: string
  country_code?: string
  region?: string
  province?: string
  municipality?: string
  city?: string
  district?: string
  latitude?: number
  longitude?: number
  email?: string
  email_source?: string
  business_status?: string
  image_count?: number
  incomplete_fields?: Array<'contact' | 'location' | 'images' | 'food_type' | 'wordpress_link'>
  is_incomplete?: boolean
}

export interface SearchResult {
  name: string
  address: string
  place_id: string
  rating: number
  postal_code?: string
  phone?: string
  website?: string
  country?: string
  country_code?: string
  region?: string
  province?: string
  municipality?: string
  city?: string
  district?: string
  latitude?: number
  longitude?: number
  email?: string
  email_source?: string
  business_status?: string
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
