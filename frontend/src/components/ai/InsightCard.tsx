'use client'

import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  AlertTriangle,
  Info,
  CheckCircle2,
  XCircle,
  Lightbulb,
} from 'lucide-react'

/** インサイト型 */
export interface Insight {
  id: string
  title: string
  description: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  confidence?: number
  evidence?: string[]
  recommendation?: string
}

interface InsightCardProps {
  insight: Insight
  className?: string
}

/** 重大度アイコンマッピング */
const SEVERITY_ICONS: Record<string, React.ReactNode> = {
  critical: <XCircle className="w-4 h-4 text-risk-critical" />,
  high: <AlertTriangle className="w-4 h-4 text-risk-high" />,
  medium: <Info className="w-4 h-4 text-risk-medium" />,
  low: <CheckCircle2 className="w-4 h-4 text-risk-low" />,
  info: <Lightbulb className="w-4 h-4 text-blue-500" />,
}

/** 重大度バッジバリアント */
const SEVERITY_VARIANT: Record<string, 'critical' | 'high' | 'medium' | 'low' | 'secondary'> = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
  info: 'secondary',
}

/** 重大度ラベル */
const SEVERITY_LABELS: Record<string, string> = {
  critical: '重大',
  high: '高',
  medium: '中',
  low: '低',
  info: '情報',
}

/**
 * AIインサイトカードコンポーネント
 * AIが生成した分析結果や推奨事項を表示するカード
 */
export function InsightCard({ insight, className }: InsightCardProps) {
  const icon = SEVERITY_ICONS[insight.severity] || SEVERITY_ICONS.info
  const badgeVariant = SEVERITY_VARIANT[insight.severity] || 'secondary'

  return (
    <Card className={cn('animate-slide-up hover:shadow-md transition-shadow', className)}>
      <CardContent className="p-5">
        {/* ヘッダー */}
        <div className="flex items-start gap-3">
          <div className="mt-0.5 shrink-0">{icon}</div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-semibold text-foreground">
                {insight.title}
              </h4>
              <Badge variant={badgeVariant} className="text-[10px]">
                {SEVERITY_LABELS[insight.severity] || insight.severity}
              </Badge>
              <span className="text-[10px] text-muted-foreground">
                {insight.category}
              </span>
            </div>

            {/* 説明 */}
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
              {insight.description}
            </p>

            {/* 信頼度 */}
            {insight.confidence !== undefined && (
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-muted-foreground">信頼度:</span>
                <div className="flex-1 max-w-[120px] h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${insight.confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs font-medium text-foreground">
                  {(insight.confidence * 100).toFixed(0)}%
                </span>
              </div>
            )}

            {/* 根拠 */}
            {insight.evidence && insight.evidence.length > 0 && (
              <div className="mt-3">
                <p className="text-xs font-medium text-muted-foreground mb-1">
                  根拠:
                </p>
                <ul className="space-y-0.5">
                  {insight.evidence.map((item, idx) => (
                    <li
                      key={idx}
                      className="text-xs text-muted-foreground pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[7px] before:w-1 before:h-1 before:rounded-full before:bg-muted-foreground/40"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 推奨事項 */}
            {insight.recommendation && (
              <div className="mt-3 p-2.5 rounded-lg bg-blue-50 border border-blue-100">
                <p className="text-xs text-blue-800">
                  <span className="font-semibold">推奨: </span>
                  {insight.recommendation}
                </p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
