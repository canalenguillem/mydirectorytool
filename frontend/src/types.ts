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

export interface UsageBreakdown {
  operation: string
  model: string
  requests: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface UsageSummary {
  days: number
  requests: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cached_tokens: number
  breakdown: UsageBreakdown[]
}

export interface SeedQueueError {
  seed_location_id: number
  name?: string
  search_term: string
  attempts: number
  last_error: string
}

export interface SeedQueueStatus {
  active: boolean
  interval_seconds: number
  next_run_at?: number
  pending: number
  processing: number
  completed: number
  failed: number
  total: number
  estimated_seconds: number
  current?: { seed_location_id: number; name?: string; country_code?: string; search_term: string; attempts: number }
  recent_errors: SeedQueueError[]
  added?: number
  retried?: number
  search_term?: string
}

export interface SeedSearch {
  search_id: number
  query: string
  total: number
  saved: number
  pending: number
}

export interface SeedCandidate extends SearchResult {
  saved: boolean
}
