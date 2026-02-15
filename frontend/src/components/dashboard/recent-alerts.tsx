'use client'

import { useState, useEffect } from 'react'
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  Clock,
  Loader2,
} from 'lucide-react'
import type { AlertSeverity } from '@/types'
import { fetchAPI } from '@/lib/api-client'

/** バックエンドアラート型 */
interface BackendAlert {
  id: string
  entity_id: string
  entity_name: string
  severity: string
  title: string
  description: string
  category: string
  is_read: boolean
  created_at: string
}

/** 重要度に応じたアイコンとカラー */
const severityConfig: Record<
  AlertSeverity,
  { icon: typeof AlertTriangle; colorClass: string; bgClass: string; label: string }
> = {
  critical: {
    icon: AlertTriangle,
    colorClass: 'text-risk-critical',
    bgClass: 'bg-risk-critical/10',
    label: 'クリティカル',
  },
  high: {
    icon: AlertCircle,
    colorClass: 'text-risk-high',
    bgClass: 'bg-risk-high/10',
    label: '高',
  },
  medium: {
    icon: Info,
    colorClass: 'text-risk-medium',
    bgClass: 'bg-risk-medium/10',
    label: '中',
  },
  low: {
    icon: CheckCircle,
    colorClass: 'text-risk-low',
    bgClass: 'bg-risk-low/10',
    label: '低',
  },
  info: {
    icon: Info,
    colorClass: 'text-blue-500',
    bgClass: 'bg-blue-500/10',
    label: '情報',
  },
}

/** 相対時間表示 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) return 'たった今'
  if (diffHours < 24) return `${diffHours}時間前`
  if (diffDays < 7) return `${diffDays}日前`
  return date.toLocaleDateString('ja-JP')
}

/**
 * 最近のアラート一覧
 * ダッシュボードにて直近のアラートを重要度アイコン付きで表示
 */
export function RecentAlerts() {
  const [alerts, setAlerts] = useState<BackendAlert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI<{ items: BackendAlert[]; total: number }>('/api/v1/risk-scores/alerts')
      .then((data) => setAlerts(data.items))
      .catch((e) => console.error('Failed to fetch alerts:', e))
      .finally(() => setLoading(false))
  }, [])

  const unreadCount = alerts.filter((a) => !a.is_read).length

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 flex items-center justify-center min-h-[200px]">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-card-foreground">
            最近のアラート
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            直近の重要通知
          </p>
        </div>
        {unreadCount > 0 && (
          <span className="rounded-full bg-risk-critical/10 px-2.5 py-0.5 text-xs font-medium text-risk-critical">
            {unreadCount} 未読
          </span>
        )}
      </div>

      <div className="space-y-3">
        {alerts.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">アラートはありません</p>
        ) : (
          alerts.map((alert) => {
            const severity = (alert.severity as AlertSeverity) || 'info'
            const config = severityConfig[severity] ?? severityConfig.info
            const Icon = config.icon

            return (
              <div
                key={alert.id}
                className={`
                  flex items-start gap-3 rounded-lg border border-border p-3
                  transition-colors hover:bg-accent/50
                  ${!alert.is_read ? 'bg-accent/30' : ''}
                `}
              >
                <div className={`mt-0.5 rounded-md ${config.bgClass} p-1.5`}>
                  <Icon className={`h-4 w-4 ${config.colorClass}`} />
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-card-foreground">
                      {alert.title}
                    </p>
                    {!alert.is_read && (
                      <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                    {alert.entity_name} - {alert.description}
                  </p>
                  <div className="mt-1.5 flex items-center gap-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${config.bgClass} ${config.colorClass}`}
                    >
                      {config.label}
                    </span>
                    <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(alert.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
