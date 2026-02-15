'use client'

import { useState, useEffect } from 'react'
import { AlertTriangle, AlertCircle, Info, CheckCircle, Loader2 } from 'lucide-react'
import { fetchAPI } from '@/lib/api-client'

/** バックエンド /api/v1/risk-scores/summary レスポンス */
interface RiskSummaryResponse {
  total_companies: number
  by_level: Record<string, number>
  avg_score: number
}

/** カード定義 */
const cardConfigs = [
  {
    key: 'critical' as const,
    label: 'クリティカル',
    labelEn: 'Critical',
    icon: AlertTriangle,
    colorClass: 'text-risk-critical',
    bgClass: 'bg-risk-critical/10',
    borderClass: 'border-risk-critical/30',
  },
  {
    key: 'high' as const,
    label: '高リスク',
    labelEn: 'High',
    icon: AlertCircle,
    colorClass: 'text-risk-high',
    bgClass: 'bg-risk-high/10',
    borderClass: 'border-risk-high/30',
  },
  {
    key: 'medium' as const,
    label: '中リスク',
    labelEn: 'Medium',
    icon: Info,
    colorClass: 'text-risk-medium',
    bgClass: 'bg-risk-medium/10',
    borderClass: 'border-risk-medium/30',
  },
  {
    key: 'low' as const,
    label: '低リスク',
    labelEn: 'Low',
    icon: CheckCircle,
    colorClass: 'text-risk-low',
    bgClass: 'bg-risk-low/10',
    borderClass: 'border-risk-low/30',
  },
]

/**
 * リスクサマリーカード
 * ダッシュボード上部に4つのカードでリスクレベル別の件数を表示
 */
export function RiskSummaryCards() {
  const [summary, setSummary] = useState<RiskSummaryResponse | null>(null)

  useEffect(() => {
    fetchAPI<RiskSummaryResponse>('/api/v1/risk-scores/summary')
      .then(setSummary)
      .catch((e) => console.error('Failed to fetch risk summary:', e))
  }, [])

  if (!summary) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cardConfigs.map((config) => {
        const Icon = config.icon
        const count = summary.by_level[config.key] ?? 0

        return (
          <div
            key={config.key}
            className={`
              rounded-xl border ${config.borderClass} ${config.bgClass}
              p-5 transition-all hover:shadow-md
            `}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {config.label}
                </p>
                <p className={`mt-2 text-3xl font-bold ${config.colorClass}`}>
                  {count}
                </p>
              </div>
              <div
                className={`rounded-lg ${config.bgClass} p-3`}
              >
                <Icon className={`h-6 w-6 ${config.colorClass}`} />
              </div>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              全{summary.total_companies}社中
            </p>
          </div>
        )
      })}
    </div>
  )
}
