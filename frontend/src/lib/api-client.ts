/**
 * API クライアント - バックエンドとの通信を管理
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** APIエラーレスポンス */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error ${status}: ${statusText}`)
    this.name = 'ApiError'
  }
}

/**
 * 汎用APIフェッチヘルパー
 * @param path - APIパス (例: /api/v1/companies)
 * @param options - fetch オプション
 * @returns パース済みレスポンスデータ
 */
export async function fetchAPI<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let data: unknown
    try {
      data = await response.json()
    } catch {
      data = await response.text()
    }
    throw new ApiError(response.status, response.statusText, data)
  }

  // 204 No Content の場合
  if (response.status === 204) {
    return undefined as unknown as T
  }

  return response.json() as Promise<T>
}

/** 型定義: ページネーションレスポンス */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

/** 型定義: 企業 */
export interface Company {
  id: string
  edinet_code: string | null
  securities_code: string | null
  name: string
  name_en: string | null
  industry_code: string | null
  industry_name: string | null
  is_listed: boolean
  country: string
  created_at: string
}

/** 型定義: 分析結果 */
export interface AnalysisResult {
  id: string
  company_id: string
  company_name: string
  fiscal_year: number
  fiscal_quarter: number
  status: string
  total_score: number | null
  risk_level: string | null
  da_score: number | null
  fraud_score: number | null
  rule_score: number | null
  benford_score: number | null
  risk_factors: string[]
  component_details: Record<string, unknown>
  created_at: string
}

/** 型定義: AIチャットリクエスト */
export interface AIChatRequest {
  message: string
  company_id?: string | null
  context?: Record<string, unknown>
  provider?: string | null
  tier?: string
  stream?: boolean
}

/** 型定義: AIチャットレスポンス */
export interface AIChatResponse {
  response: string
  provider: string
  model: string
  tokens_used: number
  cost_usd: number
}

/** 型定義: レポートリクエスト */
export interface ReportRequest {
  company_ids: string[]
  fiscal_year: number
  format: string
  sections: string[]
  language: string
}

/**
 * APIクライアントオブジェクト
 * 各エンドポイントへのアクセスメソッドを提供
 */
export const api = {
  /** 企業関連 */
  companies: {
    list: (page = 1, perPage = 20) =>
      fetchAPI<PaginatedResponse<Company>>(
        `/api/v1/companies/?page=${page}&per_page=${perPage}`
      ),
    get: (id: string) => fetchAPI<Company>(`/api/v1/companies/${id}`),
    create: (data: Partial<Company>) =>
      fetchAPI<Company>('/api/v1/companies/', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  /** 分析関連 */
  analysis: {
    run: (data: {
      company_ids: string[]
      fiscal_year: number
      fiscal_quarter?: number
      analysis_types?: string[]
    }) =>
      fetchAPI<{ status: string; results: AnalysisResult[] }>(
        '/api/v1/analysis/run',
        { method: 'POST', body: JSON.stringify(data) }
      ),
    getResults: (companyId: string) =>
      fetchAPI<{ company_id: string; results: AnalysisResult[] }>(
        `/api/v1/analysis/results/${companyId}`
      ),
    getTrend: (companyId: string) =>
      fetchAPI<{
        company_id: string
        trends: { fiscal_year: number; fiscal_quarter: number; total_score: number }[]
      }>(`/api/v1/analysis/results/${companyId}/trend`),
  },

  /** リスクスコア関連 */
  riskScores: {
    list: (params?: { risk_level?: string; min_score?: number }) => {
      const query = new URLSearchParams()
      if (params?.risk_level) query.set('risk_level', params.risk_level)
      if (params?.min_score) query.set('min_score', String(params.min_score))
      return fetchAPI<{ items: unknown[]; total: number }>(
        `/api/v1/risk-scores/?${query.toString()}`
      )
    },
    summary: () =>
      fetchAPI<{
        total_companies: number
        by_level: Record<string, number>
        avg_score: number
      }>('/api/v1/risk-scores/summary'),
    highRisk: () =>
      fetchAPI<{ items: unknown[]; total: number }>('/api/v1/risk-scores/high-risk'),
  },

  /** AI関連 */
  ai: {
    chat: (data: AIChatRequest) =>
      fetchAPI<AIChatResponse>('/api/v1/ai/chat', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    insights: (companyId: string) =>
      fetchAPI<{ company_id: string; insights: unknown[] }>(
        `/api/v1/ai/insights/${companyId}`
      ),
  },

  /** レポート関連 */
  reports: {
    generate: (data: ReportRequest) =>
      fetchAPI<{ report_id: string; status: string; download_url: string | null }>(
        '/api/v1/reports/generate',
        { method: 'POST', body: JSON.stringify(data) }
      ),
    status: (reportId: string) =>
      fetchAPI<{ report_id: string; status: string; download_url: string }>(
        `/api/v1/reports/${reportId}/status`
      ),
  },

  /** 管理関連 */
  admin: {
    status: () => fetchAPI<Record<string, unknown>>('/api/v1/admin/status'),
    budget: () => fetchAPI<Record<string, unknown>>('/api/v1/admin/budget'),
    providers: () =>
      fetchAPI<Record<string, unknown>>('/api/v1/admin/providers'),
  },

  /** ヘルスチェック */
  health: {
    check: () =>
      fetchAPI<{ status: string; version: string }>('/api/v1/health/'),
    readiness: () =>
      fetchAPI<{ status: string; timestamp: string; components: Record<string, unknown> }>(
        '/api/v1/health/readiness'
      ),
  },
}
