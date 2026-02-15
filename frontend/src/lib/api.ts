/**
 * API クライアント
 * バックエンドとの通信を管理
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/** API リクエストオプション */
interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  body?: unknown
  headers?: Record<string, string>
  params?: Record<string, string | number | boolean>
}

/** API エラー */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message?: string
  ) {
    super(message || `API Error: ${status} ${statusText}`)
    this.name = 'ApiError'
  }
}

/**
 * URLにクエリパラメータを付与
 */
function buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
  const url = new URL(path, BASE_URL)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value))
    })
  }
  return url.toString()
}

/**
 * 汎用 fetch ラッパー
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, params } = options

  const url = buildUrl(path, params)

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  }

  if (body && method !== 'GET') {
    config.body = JSON.stringify(body)
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    const errorMessage = await response.text().catch(() => '')
    throw new ApiError(response.status, response.statusText, errorMessage)
  }

  // 204 No Content の場合
  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

/**
 * API クライアント
 */
export const api = {
  /** GET リクエスト */
  get<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
    return request<T>(path, { method: 'GET', params })
  },

  /** POST リクエスト */
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'POST', body })
  },

  /** PUT リクエスト */
  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'PUT', body })
  },

  /** DELETE リクエスト */
  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' })
  },

  /** PATCH リクエスト */
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'PATCH', body })
  },
}

/**
 * API エンドポイント定義
 */
export const endpoints = {
  // 企業
  companies: '/api/v1/companies',
  company: (id: string) => `/api/v1/companies/${id}`,

  // 分析
  analyses: '/api/v1/analyses',
  analysis: (id: string) => `/api/v1/analyses/${id}`,
  runAnalysis: '/api/v1/analyses/run',

  // リスク
  riskSummary: '/api/v1/risk/summary',
  riskScores: '/api/v1/risk/scores',

  // アラート
  alerts: '/api/v1/alerts',
  alert: (id: string) => `/api/v1/alerts/${id}`,

  // 設定
  settings: '/api/v1/settings',
  aiProviders: '/api/v1/settings/ai-providers',

  // ヘルスチェック
  health: '/api/v1/health',
}
