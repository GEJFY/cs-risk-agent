'use client'

import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  Clock,
} from 'lucide-react'
import type { Alert, AlertSeverity } from '@/types'

/** デモ用アラートデータ */
const mockAlerts: Alert[] = [
  {
    id: '1',
    companyId: 'c-001',
    companyName: '東南アジア製造子会社',
    severity: 'critical',
    title: '財務報告の重大な遅延',
    message: '第3四半期の連結パッケージ提出が30日以上遅延しています。',
    category: '財務報告',
    isRead: false,
    createdAt: '2026-02-15T09:00:00Z',
  },
  {
    id: '2',
    companyId: 'c-002',
    companyName: '欧州販売子会社',
    severity: 'high',
    title: 'コンプライアンス違反の疑い',
    message: '取引先との契約条件に関するコンプライアンスリスクが検出されました。',
    category: 'コンプライアンス',
    isRead: false,
    createdAt: '2026-02-14T15:30:00Z',
  },
  {
    id: '3',
    companyId: 'c-003',
    companyName: '北米IT子会社',
    severity: 'medium',
    title: 'IT セキュリティ監査の指摘事項',
    message: 'アクセス権管理に関する改善勧告が発行されています。',
    category: 'ITセキュリティ',
    isRead: true,
    createdAt: '2026-02-14T10:00:00Z',
  },
  {
    id: '4',
    companyId: 'c-004',
    companyName: '中国物流子会社',
    severity: 'high',
    title: '為替リスクの増大',
    message: 'CNY/JPY為替変動により、想定以上の為替差損リスクが発生しています。',
    category: '財務リスク',
    isRead: true,
    createdAt: '2026-02-13T16:45:00Z',
  },
  {
    id: '5',
    companyId: 'c-005',
    companyName: 'インド開発子会社',
    severity: 'low',
    title: '定期監査完了',
    message: '年次内部監査が完了し、重大な指摘事項はありませんでした。',
    category: '内部監査',
    isRead: true,
    createdAt: '2026-02-13T09:00:00Z',
  },
]

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
        <span className="rounded-full bg-risk-critical/10 px-2.5 py-0.5 text-xs font-medium text-risk-critical">
          {mockAlerts.filter((a) => !a.isRead).length} 未読
        </span>
      </div>

      <div className="space-y-3">
        {mockAlerts.map((alert) => {
          const config = severityConfig[alert.severity]
          const Icon = config.icon

          return (
            <div
              key={alert.id}
              className={`
                flex items-start gap-3 rounded-lg border border-border p-3
                transition-colors hover:bg-accent/50
                ${!alert.isRead ? 'bg-accent/30' : ''}
              `}
            >
              {/* 重要度アイコン */}
              <div className={`mt-0.5 rounded-md ${config.bgClass} p-1.5`}>
                <Icon className={`h-4 w-4 ${config.colorClass}`} />
              </div>

              {/* アラート内容 */}
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-card-foreground">
                    {alert.title}
                  </p>
                  {!alert.isRead && (
                    <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-primary" />
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                  {alert.companyName} - {alert.message}
                </p>
                <div className="mt-1.5 flex items-center gap-3">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${config.bgClass} ${config.colorClass}`}
                  >
                    {config.label}
                  </span>
                  <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {formatRelativeTime(alert.createdAt)}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
