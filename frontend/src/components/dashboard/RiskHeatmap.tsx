'use client'

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ZAxis,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

/** データポイント型 */
interface DataPoint {
  name: string
  totalScore: number
  fraudScore: number
  size: number
  riskLevel: 'critical' | 'high' | 'medium' | 'low'
}

interface RiskHeatmapProps {
  /** 表示データ */
  data?: DataPoint[]
  /** カードタイトル */
  title?: string
  /** カスタムクラス */
  className?: string
}

/** リスクレベルカラーマッピング */
const RISK_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
}

/** デフォルトデモデータ */
const DEFAULT_DATA: DataPoint[] = [
  { name: 'グローバルテック', totalScore: 82, fraudScore: 78, size: 120, riskLevel: 'critical' },
  { name: '東京エレクトロニクス', totalScore: 65, fraudScore: 60, size: 95, riskLevel: 'high' },
  { name: '大阪製薬', totalScore: 48, fraudScore: 42, size: 80, riskLevel: 'medium' },
  { name: '未来通信', totalScore: 55, fraudScore: 50, size: 110, riskLevel: 'medium' },
  { name: 'サクラ精密', totalScore: 30, fraudScore: 25, size: 60, riskLevel: 'low' },
  { name: '北海道フーズ', totalScore: 72, fraudScore: 68, size: 85, riskLevel: 'high' },
  { name: '九州テクノ', totalScore: 38, fraudScore: 35, size: 70, riskLevel: 'low' },
  { name: '名古屋重工', totalScore: 58, fraudScore: 52, size: 100, riskLevel: 'medium' },
  { name: '横浜バイオ', totalScore: 88, fraudScore: 85, size: 130, riskLevel: 'critical' },
  { name: '京都半導体', totalScore: 42, fraudScore: 38, size: 75, riskLevel: 'medium' },
]

/** カスタムツールチップ */
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload as DataPoint
  return (
    <div className="bg-card border border-border rounded-lg p-3 shadow-lg">
      <p className="font-semibold text-sm text-foreground">{data.name}</p>
      <div className="mt-1 space-y-0.5 text-xs text-muted-foreground">
        <p>総合スコア: <span className="font-medium text-foreground">{data.totalScore}</span></p>
        <p>不正スコア: <span className="font-medium text-foreground">{data.fraudScore}</span></p>
      </div>
    </div>
  )
}

/**
 * リスクヒートマップコンポーネント
 * ScatterChart で企業のリスク分布を可視化する
 */
export function RiskHeatmap({
  data = DEFAULT_DATA,
  title = 'リスク分布マップ',
  className,
}: RiskHeatmapProps) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                opacity={0.5}
              />
              <XAxis
                type="number"
                dataKey="totalScore"
                name="総合リスクスコア"
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                label={{
                  value: '総合リスクスコア',
                  position: 'insideBottom',
                  offset: -10,
                  style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' },
                }}
              />
              <YAxis
                type="number"
                dataKey="fraudScore"
                name="不正リスクスコア"
                domain={[0, 100]}
                tick={{ fontSize: 11 }}
                label={{
                  value: '不正リスクスコア',
                  angle: -90,
                  position: 'insideLeft',
                  offset: 10,
                  style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' },
                }}
              />
              <ZAxis type="number" dataKey="size" range={[40, 200]} />
              <Tooltip content={<CustomTooltip />} />
              <Scatter data={data}>
                {data.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={RISK_COLORS[entry.riskLevel] || RISK_COLORS.low}
                    fillOpacity={0.7}
                    stroke={RISK_COLORS[entry.riskLevel] || RISK_COLORS.low}
                    strokeWidth={1}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* 凡例 */}
        <div className="flex items-center justify-center gap-4 mt-2">
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <div key={level} className="flex items-center gap-1.5">
              <div
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span className="text-xs text-muted-foreground capitalize">
                {level === 'critical' ? '重大' : level === 'high' ? '高' : level === 'medium' ? '中' : '低'}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
