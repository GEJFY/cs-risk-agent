'use client'

import { useState, useEffect } from 'react'
import { useAppStore } from '@/stores/app-store'
import {
  Settings,
  Brain,
  DollarSign,
  Bell,
  Shield,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  RefreshCw,
  Star,
} from 'lucide-react'
import { fetchAPI } from '@/lib/api-client'

/** バックエンドから取得するプロバイダー情報 */
interface ProviderInfo {
  id: string
  name: string
  configured: boolean
  status: 'active' | 'inactive'
  sota_model: string
  cost_effective_model: string
}

/** /api/v1/admin/status レスポンス */
interface AdminStatus {
  mode: string
  default_provider: string
  fallback_chain: string[]
  providers: Record<string, ProviderInfo & { status: string }>
  budget: {
    monthly_limit_usd: number
    alert_threshold: number
    circuit_breaker_threshold: number
  }
}

/** /api/v1/admin/budget レスポンス */
interface BudgetStatus {
  state: string
  monthly_limit_usd: number
  current_spend_usd: number
  remaining_usd: number
  usage_ratio: number
}

/** /api/v1/admin/cost レスポンス */
interface CostSummary {
  total_cost_usd: number
  total_requests: number
  by_provider: Record<string, number>
  by_model: Record<string, number>
}

/** ステータスの表示設定 */
const statusConfig = {
  active: {
    icon: CheckCircle,
    label: '稼働中',
    colorClass: 'text-risk-low',
    bgClass: 'bg-risk-low/10',
  },
  inactive: {
    icon: XCircle,
    label: '未設定',
    colorClass: 'text-muted-foreground',
    bgClass: 'bg-muted',
  },
  error: {
    icon: AlertCircle,
    label: 'エラー',
    colorClass: 'text-risk-critical',
    bgClass: 'bg-risk-critical/10',
  },
}

/**
 * 設定ページ
 * AIプロバイダーの状態、予算情報、通知設定を表示
 */
export default function SettingsPage() {
  const { sidebarOpen } = useAppStore()
  const [adminStatus, setAdminStatus] = useState<AdminStatus | null>(null)
  const [budgetStatus, setBudgetStatus] = useState<BudgetStatus | null>(null)
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [settingDefault, setSettingDefault] = useState<string | null>(null)

  /** データ取得 */
  const fetchData = async () => {
    setLoading(true)
    try {
      const [status, budget, cost] = await Promise.all([
        fetchAPI<AdminStatus>('/api/v1/admin/status'),
        fetchAPI<BudgetStatus>('/api/v1/admin/budget'),
        fetchAPI<CostSummary>('/api/v1/admin/cost'),
      ])
      setAdminStatus(status)
      setBudgetStatus(budget)
      setCostSummary(cost)
    } catch (e) {
      console.error('Failed to fetch admin data:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  /** デフォルトプロバイダー変更 */
  const handleSetDefault = async (providerId: string) => {
    setSettingDefault(providerId)
    try {
      await fetchAPI(`/api/v1/admin/providers/${providerId}/set-default`, { method: 'POST' })
      await fetchData()
    } catch (e) {
      console.error('Failed to set default provider:', e)
    } finally {
      setSettingDefault(null)
    }
  }

  const budgetLimit = budgetStatus?.monthly_limit_usd ?? 0
  const currentSpend = budgetStatus?.current_spend_usd ?? costSummary?.total_cost_usd ?? 0
  const usagePct = budgetLimit > 0 ? (currentSpend / budgetLimit) * 100 : 0

  const providerOrder = ['azure', 'aws', 'gcp', 'ollama']

  return (
    <div
      className={`
        space-y-6 transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* ページヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-2.5">
            <Settings className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">設定</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              AIプロバイダーとシステム設定の管理
            </p>
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          更新
        </button>
      </div>

      {loading && !adminStatus ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : (
        <>
          {/* 予算サマリー */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-4 flex items-center gap-2">
              <DollarSign className="h-5 w-5 text-primary" />
              <h3 className="text-base font-semibold text-card-foreground">
                AI利用予算
              </h3>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-sm text-muted-foreground">月間予算上限</p>
                <p className="text-2xl font-bold text-card-foreground">
                  ${budgetLimit.toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">今月の使用額</p>
                <p className="text-2xl font-bold text-card-foreground">
                  ${currentSpend.toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">残り予算</p>
                <p className="text-2xl font-bold text-card-foreground">
                  ${(budgetLimit - currentSpend).toFixed(2)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">API呼び出し数</p>
                <p className="text-2xl font-bold text-card-foreground">
                  {costSummary?.total_requests ?? 0}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <div className="h-3 w-full rounded-full bg-muted">
                <div
                  className={`h-3 rounded-full transition-all ${
                    usagePct > 80
                      ? 'bg-risk-critical'
                      : usagePct > 50
                        ? 'bg-risk-medium'
                        : 'bg-risk-low'
                  }`}
                  style={{ width: `${Math.min(usagePct, 100)}%` }}
                />
              </div>
              <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                <span>使用率: {usagePct.toFixed(1)}%</span>
                <span>
                  サーキットブレーカー: {budgetStatus?.state === 'closed' ? '正常' : '発動中'}
                </span>
              </div>
            </div>
          </div>

          {/* AIプロバイダー設定 */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-2 flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              <h3 className="text-base font-semibold text-card-foreground">
                AIプロバイダー
              </h3>
            </div>
            <p className="mb-4 text-xs text-muted-foreground">
              モード: {adminStatus?.mode ?? '-'} / フォールバック: {adminStatus?.fallback_chain?.join(' → ') ?? '-'}
            </p>

            <div className="space-y-4">
              {providerOrder.map((pid) => {
                const prov = adminStatus?.providers?.[pid]
                if (!prov) return null
                const isDefault = adminStatus?.default_provider === pid
                const status = prov.configured ? 'active' : 'inactive'
                const config = statusConfig[status]
                const StatusIcon = config.icon

                return (
                  <div
                    key={pid}
                    className={`rounded-lg border p-4 ${isDefault ? 'border-primary bg-primary/5' : 'border-border'}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-sm font-bold text-muted-foreground">
                          {pid === 'azure' ? 'Az' : pid === 'aws' ? 'AW' : pid === 'gcp' ? 'GC' : 'OL'}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-card-foreground">
                              {prov.name}
                            </p>
                            {isDefault && (
                              <span className="inline-flex items-center gap-0.5 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                                <Star className="h-2.5 w-2.5" />
                                デフォルト
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            SOTA: {prov.sota_model} / コスト最適: {prov.cost_effective_model}
                          </p>
                        </div>
                      </div>
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.bgClass} ${config.colorClass}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {config.label}
                      </span>
                    </div>

                    <div className="mt-3 flex items-center gap-2 border-t border-border pt-3">
                      {!isDefault && prov.configured && (
                        <button
                          onClick={() => handleSetDefault(pid)}
                          disabled={settingDefault === pid}
                          className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                        >
                          {settingDefault === pid ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            'デフォルトに設定'
                          )}
                        </button>
                      )}
                      {!prov.configured && (
                        <p className="text-xs text-muted-foreground">
                          .env ファイルでAPIキーを設定してください
                        </p>
                      )}
                      {prov.configured && (
                        <span className="text-xs text-risk-low">APIキー設定済み</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* 通知設定 */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-4 flex items-center gap-2">
              <Bell className="h-5 w-5 text-primary" />
              <h3 className="text-base font-semibold text-card-foreground">
                通知設定
              </h3>
            </div>

            <div className="space-y-4">
              {[
                {
                  label: 'クリティカルリスクアラート',
                  description: 'リスクスコア80以上の検出時に通知',
                  enabled: true,
                },
                {
                  label: '分析完了通知',
                  description: 'リスク分析の完了時に通知',
                  enabled: true,
                },
                {
                  label: '日次サマリーレポート',
                  description: '毎日のリスク状況サマリーを送信',
                  enabled: false,
                },
                {
                  label: '予算アラート',
                  description: `AI使用料が予算の${((adminStatus?.budget?.alert_threshold ?? 0.8) * 100).toFixed(0)}%を超えた場合に通知`,
                  enabled: true,
                },
              ].map((setting) => (
                <div
                  key={setting.label}
                  className="flex items-center justify-between rounded-lg border border-border p-4"
                >
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      {setting.label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {setting.description}
                    </p>
                  </div>
                  <div
                    className={`
                      relative h-6 w-11 cursor-pointer rounded-full transition-colors
                      ${setting.enabled ? 'bg-primary' : 'bg-muted'}
                    `}
                  >
                    <div
                      className={`
                        absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform
                        ${setting.enabled ? 'translate-x-5' : 'translate-x-0.5'}
                      `}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* リスク閾値設定 */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="mb-4 flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <h3 className="text-base font-semibold text-card-foreground">
                リスク閾値設定
              </h3>
            </div>

            <p className="mb-4 text-sm text-muted-foreground">
              リスクレベルの判定に使用するスコア閾値を設定
            </p>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {[
                {
                  level: 'クリティカル',
                  threshold: 80,
                  color: 'border-risk-critical',
                  textColor: 'text-risk-critical',
                },
                {
                  level: '高リスク',
                  threshold: 60,
                  color: 'border-risk-high',
                  textColor: 'text-risk-high',
                },
                {
                  level: '中リスク',
                  threshold: 40,
                  color: 'border-risk-medium',
                  textColor: 'text-risk-medium',
                },
              ].map((item) => (
                <div
                  key={item.level}
                  className={`rounded-lg border-l-4 ${item.color} border border-border p-4`}
                >
                  <p className={`text-sm font-medium ${item.textColor}`}>
                    {item.level}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <input
                      type="number"
                      defaultValue={item.threshold}
                      min={0}
                      max={100}
                      className="w-20 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <span className="text-sm text-muted-foreground">以上</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-4 flex justify-end">
              <button className="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
                設定を保存
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
