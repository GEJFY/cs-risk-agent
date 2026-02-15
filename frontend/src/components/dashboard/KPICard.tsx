'use client'

import { cn } from '@/lib/utils'
import { Card, CardContent } from '@/components/ui/card'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface KPICardProps {
  /** カードタイトル */
  title: string
  /** 表示値 */
  value: string | number
  /** 前期比変動（パーセント） */
  delta?: number | null
  /** アイコン */
  icon?: React.ReactNode
  /** カスタムクラス */
  className?: string
  /** 値のサフィックス（単位など） */
  suffix?: string
  /** 変動の色を反転（コストなど低い方が良い指標） */
  invertDelta?: boolean
}

/**
 * KPIカードコンポーネント
 * ダッシュボード上部に配置される主要指標表示カード
 */
export function KPICard({
  title,
  value,
  delta,
  icon,
  className,
  suffix,
  invertDelta = false,
}: KPICardProps) {
  const getDeltaColor = () => {
    if (delta === null || delta === undefined) return 'text-muted-foreground'
    const isPositive = invertDelta ? delta < 0 : delta > 0
    const isNegative = invertDelta ? delta > 0 : delta < 0
    if (isPositive) return 'text-green-600'
    if (isNegative) return 'text-red-600'
    return 'text-muted-foreground'
  }

  const getDeltaIcon = () => {
    if (delta === null || delta === undefined) return <Minus className="w-3 h-3" />
    if (delta > 0) return <TrendingUp className="w-3 h-3" />
    if (delta < 0) return <TrendingDown className="w-3 h-3" />
    return <Minus className="w-3 h-3" />
  }

  return (
    <Card className={cn('animate-fade-in', className)}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              {title}
            </p>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-bold text-foreground">
                {value}
              </span>
              {suffix && (
                <span className="text-sm text-muted-foreground">{suffix}</span>
              )}
            </div>
            {delta !== null && delta !== undefined && (
              <div
                className={cn(
                  'flex items-center gap-1 text-xs font-medium',
                  getDeltaColor()
                )}
              >
                {getDeltaIcon()}
                <span>
                  {delta > 0 ? '+' : ''}
                  {delta.toFixed(1)}%
                </span>
                <span className="text-muted-foreground ml-1">前期比</span>
              </div>
            )}
          </div>
          {icon && (
            <div className="p-2 rounded-lg bg-muted text-muted-foreground">
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
