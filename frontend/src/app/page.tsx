'use client'

import { RiskSummaryCards } from '@/components/dashboard/risk-summary-cards'
import { RiskChart } from '@/components/dashboard/risk-chart'
import { RecentAlerts } from '@/components/dashboard/recent-alerts'
import { useAppStore } from '@/stores/app-store'
import { Activity, TrendingUp, Clock } from 'lucide-react'

/**
 * ダッシュボードページ
 * リスク概要、スコア分布チャート、最近のアラートを表示
 */
export default function DashboardPage() {
  const { sidebarOpen } = useAppStore()

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
            連結子会社のリスク状況を一目で把握
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            最終更新: 2026-02-15 10:30
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
              <p className="text-sm text-muted-foreground">総分析数</p>
              <p className="text-2xl font-bold text-card-foreground">156</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            今月: +23件
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-risk-medium/10 p-2.5">
              <TrendingUp className="h-5 w-5 text-risk-medium" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">平均リスクスコア</p>
              <p className="text-2xl font-bold text-card-foreground">54.2</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            前月比: +2.3pt
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-risk-critical/10 p-2.5">
              <Activity className="h-5 w-5 text-risk-critical" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">未対応アラート</p>
              <p className="text-2xl font-bold text-card-foreground">8</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-risk-critical">
            クリティカル: 2件
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
