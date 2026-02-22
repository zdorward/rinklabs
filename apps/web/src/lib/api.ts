// apps/web/src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface GameSummary {
  id: string
  home_team: string
  away_team: string
  commence_time: string
  consensus_home_prob: number
  consensus_away_prob: number
  best_edge: {
    side: string
    bookmaker: string
    ev_pct: number
  } | null
  disagreement: number
  books_count: number
}

export interface EdgeOpportunity {
  game_id: string
  home_team: string
  away_team: string
  commence_time: string
  side: string
  bookmaker: string
  ev_pct: number
  book_price: number
  consensus_prob: number
}

export interface DisagreementInfo {
  game_id: string
  home_team: string
  away_team: string
  commence_time: string
  disagreement_pct: number
  range: { min_prob: number; max_prob: number }
}

export interface TopEdgesResponse {
  edges: EdgeOpportunity[]
  truncated: boolean
  total_count: number
}

export interface TopDisagreementsResponse {
  disagreements: DisagreementInfo[]
  truncated: boolean
  total_count: number
}

export interface UserInfo {
  id: string
  email: string | null
  subscription_status: string
  current_period_end: string | null
  stripe_customer_id: string | null
}

export interface BookOdds {
  bookmaker: string
  home_price: number
  away_price: number
  home_vig_free_prob: number
  away_vig_free_prob: number
  home_edge_ev: number
  away_edge_ev: number
  last_updated: string
}

export interface GameDetail {
  id: string
  home_team: string
  away_team: string
  commence_time: string
  consensus: {
    home_prob: number
    away_prob: number
  }
  odds_by_book: BookOdds[]
  movement: {
    home_open: number | null
    home_current: number
    change_from_open: number | null
    change_24h: number | null
  }
  disagreement: number
}

export interface OddsSnapshot {
  timestamp: string
  consensus_home_prob: number
  books: {
    bookmaker: string
    home_price: number
    away_price: number
  }[]
}

export interface OddsHistoryResponse {
  game_id: string
  snapshots: OddsSnapshot[]
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit & { token?: string }
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }

  if (options?.token) {
    headers['Authorization'] = `Bearer ${options.token}`
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: { ...headers, ...options?.headers },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`)
  }

  return response.json()
}

export const api = {
  getGames: (date: string) =>
    fetchApi<{ games: GameSummary[] }>(`/games?date=${date}`),

  getGame: (gameId: string) =>
    fetchApi<GameDetail>(`/games/${gameId}`),

  getGameOddsHistory: (gameId: string) =>
    fetchApi<OddsHistoryResponse>(`/games/${gameId}/odds`),

  getTopEdges: (limit?: number) =>
    fetchApi<TopEdgesResponse>(`/markets/today/top-edges${limit ? `?limit=${limit}` : ''}`),

  getTopDisagreements: (limit?: number) =>
    fetchApi<TopDisagreementsResponse>(`/markets/today/top-disagreements${limit ? `?limit=${limit}` : ''}`),

  getMe: (token: string) =>
    fetchApi<UserInfo>('/me', { token }),
}
