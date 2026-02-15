/**
 * CS Risk Agent 型定義
 * 連結子会社リスク分析ツールで使用するTypeScript型
 */

/** リスクレベル */
export type RiskLevel = 'critical' | 'high' | 'medium' | 'low'

/** アラート重要度 */
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

/** 分析ステータス */
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed'

/** 企業情報 */
export interface Company {
  id: string
  name: string
  nameEn?: string
  country: string
  region: string
  ownershipPct: number
  consolidationType: 'full' | 'equity' | 'proportional'
  industry: string
  fiscalYearEnd: string
  lastAnalysisDate?: string
  riskScore?: number
  riskLevel?: RiskLevel
}

/** リスクスコア */
export interface RiskScore {
  companyId: string
  companyName: string
  overallScore: number
  riskLevel: RiskLevel
  financialScore: number
  operationalScore: number
  complianceScore: number
  strategicScore: number
  updatedAt: string
}

/** リスクカテゴリ別詳細 */
export interface RiskCategory {
  name: string
  nameJa: string
  score: number
  maxScore: number
  findings: string[]
}

/** 分析結果 */
export interface AnalysisResult {
  id: string
  companyId: string
  companyName: string
  status: AnalysisStatus
  riskScore: RiskScore
  categories: RiskCategory[]
  summary: string
  recommendations: string[]
  aiModel: string
  analyzedAt: string
  duration: number // 分析所要時間(秒)
}

/** アラート */
export interface Alert {
  id: string
  companyId: string
  companyName: string
  severity: AlertSeverity
  title: string
  message: string
  category: string
  isRead: boolean
  createdAt: string
}

/** リスクサマリー (ダッシュボード用) */
export interface RiskSummary {
  critical: number
  high: number
  medium: number
  low: number
  totalCompanies: number
  lastUpdated: string
}

/** AI プロバイダー設定 */
export interface AIProviderConfig {
  provider: string
  model: string
  status: 'active' | 'inactive' | 'error'
  apiKeyConfigured: boolean
  monthlyBudget: number
  monthlyUsage: number
  lastUsed?: string
}

/** アプリケーション設定 */
export interface AppSettings {
  aiProviders: AIProviderConfig[]
  analysisSchedule: string
  notificationsEnabled: boolean
  riskThresholds: {
    critical: number
    high: number
    medium: number
  }
}

/** API レスポンス */
export interface ApiResponse<T> {
  data: T
  message?: string
  status: 'success' | 'error'
}

/** ページネーション */
export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  perPage: number
  totalPages: number
}
