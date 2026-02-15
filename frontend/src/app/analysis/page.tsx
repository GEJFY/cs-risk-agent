'use client'

import { AnalysisForm } from '@/components/analysis/analysis-form'
import { useAppStore } from '@/stores/app-store'
import { PlayCircle, History, Clock } from 'lucide-react'

/** 最近の分析履歴 (デモ用) */
const recentAnalyses = [
  {
    id: 'a-001',
    companyName: '東南アジア製造子会社',
    type: '総合リスク分析',
    status: 'completed' as const,
    score: 87,
    date: '2026-02-15 09:30',
    duration: '4分12秒',
  },
  {
    id: 'a-002',
    companyName: '欧州販売子会社',
    type: '財務リスク分析',
    status: 'completed' as const,
    score: 72,
    date: '2026-02-14 16:00',
    duration: '1分45秒',
  },
  {
    id: 'a-003',
    companyName: '北米IT子会社',
    type: 'コンプライアンス分析',
    status: 'completed' as const,
    score: 55,
    date: '2026-02-14 14:20',
    duration: '2分30秒',
  },
  {
    id: 'a-004',
    companyName: '中国物流子会社',
    type: '総合リスク分析',
    status: 'completed' as const,
    score: 68,
    date: '2026-02-13 11:00',
    duration: '3分58秒',
  },
]

/**
 * 分析実行ページ
 * 企業を選択して各種リスク分析を実行
 */
export default function AnalysisPage() {
  const { sidebarOpen } = useAppStore()

  return (
    <div
      className={`
        space-y-6 transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* ページヘッダー */}
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2.5">
          <PlayCircle className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">分析実行</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            AI を活用した連結子会社リスク分析
          </p>
        </div>
      </div>

      {/* 分析フォーム */}
      <AnalysisForm />

      {/* 分析履歴 */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <History className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            最近の分析履歴
          </h3>
        </div>

        <div className="space-y-3">
          {recentAnalyses.map((analysis) => (
            <div
              key={analysis.id}
              className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-accent/30 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div
                  className={`
                    h-10 w-10 rounded-lg flex items-center justify-center text-sm font-bold
                    ${
                      analysis.score >= 80
                        ? 'bg-risk-critical/10 text-risk-critical'
                        : analysis.score >= 60
                          ? 'bg-risk-high/10 text-risk-high'
                          : analysis.score >= 40
                            ? 'bg-risk-medium/10 text-risk-medium'
                            : 'bg-risk-low/10 text-risk-low'
                    }
                  `}
                >
                  {analysis.score}
                </div>
                <div>
                  <p className="text-sm font-medium text-card-foreground">
                    {analysis.companyName}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {analysis.type}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">{analysis.date}</p>
                <div className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {analysis.duration}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
