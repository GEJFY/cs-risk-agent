'use client'

import { useState, useEffect } from 'react'
import { RiskSummaryCards } from '@/components/dashboard/risk-summary-cards'
import { RiskChart } from '@/components/dashboard/risk-chart'
import { RecentAlerts } from '@/components/dashboard/recent-alerts'
import { useAppStore } from '@/stores/app-store'
import { Activity, TrendingUp, Clock, AlertTriangle } from 'lucide-react'
import { fetchAPI } from '@/lib/api-client'

/** サマリーデータ */
interface SummaryData {
  total_companies: number
  by_level: Record<string, number>
  avg_score: number
}

/**
 * ダッシュボードページ
 * リスク概要、スコア分布チャート、最近のアラートを表示
 */
export default function DashboardPage() {
  const { sidebarOpen } = useAppStore()
  const [summary, setSummary] = useState<SummaryData | null>(null)
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    fetchAPI<SummaryData>('/api/v1/risk-scores/summary')
      .then(setSummary)
      .catch((e) => console.error('Failed to fetch summary:', e))

    fetchAPI<{ items: unknown[]; total: number }>('/api/v1/risk-scores/alerts')
      .then((data) => setAlertCount(data.total))
      .catch((e) => console.error('Failed to fetch alerts:', e))
  }, [])

  const criticalCount = summary?.by_level?.critical ?? 0
  const highCount = summary?.by_level?.high ?? 0

  return (
    <div
      className={`
        space-y-6 transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* ページヘッダー */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            ダッシュボード
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            東洋重工グループ 連結子会社リスク状況
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            最終更新: {new Date().toLocaleDateString('ja-JP')}
          </div>
        </div>
      </div>

      {/* サマリー統計カード */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2.5">
              <Activity className="h-5 w-5 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">対象子会社数</p>
              <p className="text-2xl font-bold text-card-foreground">
                {summary?.total_companies ?? '-'}
              </p>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            連結子会社 + 親会社
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-risk-medium/10 p-2.5">
              <TrendingUp className="h-5 w-5 text-risk-medium" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">平均リスクスコア</p>
              <p className="text-2xl font-bold text-card-foreground">
                {summary?.avg_score ?? '-'}
              </p>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            全社平均（100点満点）
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-risk-critical/10 p-2.5">
              <AlertTriangle className="h-5 w-5 text-risk-critical" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">要注意アラート</p>
              <p className="text-2xl font-bold text-card-foreground">{alertCount}</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-risk-critical">
            Critical: {criticalCount}社 / High: {highCount}社
          </p>
        </div>
      </div>

      {/* リスクレベル別カード */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-foreground">
          リスクレベル別サマリー
        </h2>
        <RiskSummaryCards />
      </div>

      {/* チャートとアラートの2カラム */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RiskChart />
        <RecentAlerts />
      </div>
    </div>
  )
}
