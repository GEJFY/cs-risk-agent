'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { FilterBar } from '@/components/dashboard/FilterBar'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

/** セグメントモックデータ */
const segmentData = [
  {
    id: '1',
    name: 'エレクトロニクス事業',
    parent: 'グローバルテック株式会社',
    revenue: 45000,
    operatingIncome: 3200,
    riskScore: 72,
    riskLevel: 'high' as const,
    margin: 7.1,
    growth: 15.2,
    subsidiaryCount: 8,
  },
  {
    id: '2',
    name: 'バイオテクノロジー事業',
    parent: '横浜バイオ株式会社',
    revenue: 28000,
    operatingIncome: -1200,
    riskScore: 85,
    riskLevel: 'critical' as const,
    margin: -4.3,
    growth: -8.5,
    subsidiaryCount: 5,
  },
  {
    id: '3',
    name: '食品加工事業',
    parent: '北海道フーズ株式会社',
    revenue: 62000,
    operatingIncome: 4100,
    riskScore: 45,
    riskLevel: 'medium' as const,
    margin: 6.6,
    growth: 3.2,
    subsidiaryCount: 12,
  },
  {
    id: '4',
    name: '通信インフラ事業',
    parent: '未来通信株式会社',
    revenue: 38000,
    operatingIncome: 5200,
    riskScore: 32,
    riskLevel: 'low' as const,
    margin: 13.7,
    growth: 8.1,
    subsidiaryCount: 6,
  },
  {
    id: '5',
    name: '半導体製造事業',
    parent: '京都半導体株式会社',
    revenue: 52000,
    operatingIncome: 8500,
    riskScore: 38,
    riskLevel: 'low' as const,
    margin: 16.3,
    growth: 22.5,
    subsidiaryCount: 4,
  },
  {
    id: '6',
    name: '重工業事業',
    parent: '名古屋重工株式会社',
    revenue: 95000,
    operatingIncome: 6800,
    riskScore: 55,
    riskLevel: 'medium' as const,
    margin: 7.2,
    growth: -2.1,
    subsidiaryCount: 15,
  },
  {
    id: '7',
    name: '精密機器事業',
    parent: 'サクラ精密工業株式会社',
    revenue: 22000,
    operatingIncome: 3100,
    riskScore: 28,
    riskLevel: 'low' as const,
    margin: 14.1,
    growth: 5.8,
    subsidiaryCount: 3,
  },
  {
    id: '8',
    name: '医薬品研究事業',
    parent: '大阪製薬株式会社',
    revenue: 41000,
    operatingIncome: 2400,
    riskScore: 62,
    riskLevel: 'high' as const,
    margin: 5.9,
    growth: -5.3,
    subsidiaryCount: 7,
  },
]

/** スキャッタープロットデータ変換 */
const scatterData = segmentData.map((s) => ({
  name: s.name,
  margin: s.margin,
  growth: s.growth,
  riskScore: s.riskScore,
  riskLevel: s.riskLevel,
  revenue: s.revenue,
}))

/** リスクカラーマッピング */
const RISK_COLORS: Record<string, string> = {
  critical: '#dc2626',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
}

/** カスタムツールチップ */
function SegmentTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const data = payload[0]?.payload
  return (
    <div className="bg-card border border-border rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold text-sm">{data.name}</p>
      <p className="mt-1 text-muted-foreground">
        営業利益率: <span className="text-foreground font-medium">{data.margin}%</span>
      </p>
      <p className="text-muted-foreground">
        成長率: <span className="text-foreground font-medium">{data.growth}%</span>
      </p>
      <p className="text-muted-foreground">
        リスクスコア: <span className="text-foreground font-medium">{data.riskScore}</span>
      </p>
    </div>
  )
}

/**
 * S02: セグメント分析ページ
 * 事業セグメント単位でのリスク分析と財務データ比較
 */
export default function SegmentsPage() {
  const [sortField, setSortField] = useState<'riskScore' | 'revenue' | 'margin'>('riskScore')
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = [...segmentData].sort((a, b) => {
    const diff = a[sortField] - b[sortField]
    return sortAsc ? diff : -diff
  })

  const handleSort = (field: 'riskScore' | 'revenue' | 'margin') => {
    if (sortField === field) {
      setSortAsc(!sortAsc)
    } else {
      setSortField(field)
      setSortAsc(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">セグメント分析</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          事業セグメント別のリスク分析と財務指標比較
        </p>
      </div>

      <FilterBar />

      {/* スキャッタープロット */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">
            セグメント リスクマップ（営業利益率 vs 成長率）
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  opacity={0.5}
                />
                <XAxis
                  type="number"
                  dataKey="margin"
                  name="営業利益率"
                  unit="%"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: '営業利益率 (%)',
                    position: 'insideBottom',
                    offset: -15,
                    style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' },
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="growth"
                  name="成長率"
                  unit="%"
                  tick={{ fontSize: 11 }}
                  label={{
                    value: '売上成長率 (%)',
                    angle: -90,
                    position: 'insideLeft',
                    offset: 10,
                    style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' },
                  }}
                />
                <Tooltip content={<SegmentTooltip />} />
                <Scatter data={scatterData}>
                  {scatterData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={RISK_COLORS[entry.riskLevel]}
                      fillOpacity={0.7}
                      r={Math.max(6, entry.riskScore / 8)}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* セグメントテーブル */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">セグメント一覧</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground">
                    セグメント名
                  </th>
                  <th className="text-left py-3 px-2 text-xs font-medium text-muted-foreground">
                    親会社
                  </th>
                  <th
                    className="text-right py-3 px-2 text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                    onClick={() => handleSort('revenue')}
                  >
                    売上高（百万円）{sortField === 'revenue' ? (sortAsc ? ' ^' : ' v') : ''}
                  </th>
                  <th
                    className="text-right py-3 px-2 text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                    onClick={() => handleSort('margin')}
                  >
                    営業利益率{sortField === 'margin' ? (sortAsc ? ' ^' : ' v') : ''}
                  </th>
                  <th className="text-right py-3 px-2 text-xs font-medium text-muted-foreground">
                    成長率
                  </th>
                  <th
                    className="text-right py-3 px-2 text-xs font-medium text-muted-foreground cursor-pointer hover:text-foreground"
                    onClick={() => handleSort('riskScore')}
                  >
                    リスクスコア{sortField === 'riskScore' ? (sortAsc ? ' ^' : ' v') : ''}
                  </th>
                  <th className="text-center py-3 px-2 text-xs font-medium text-muted-foreground">
                    レベル
                  </th>
                  <th className="text-right py-3 px-2 text-xs font-medium text-muted-foreground">
                    子会社数
                  </th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((seg) => (
                  <tr
                    key={seg.id}
                    className="border-b border-border last:border-0 hover:bg-muted/50 transition-colors"
                  >
                    <td className="py-2.5 px-2 font-medium text-foreground">
                      {seg.name}
                    </td>
                    <td className="py-2.5 px-2 text-muted-foreground text-xs">
                      {seg.parent}
                    </td>
                    <td className="py-2.5 px-2 text-right tabular-nums">
                      {seg.revenue.toLocaleString()}
                    </td>
                    <td
                      className={`py-2.5 px-2 text-right tabular-nums ${
                        seg.margin < 0 ? 'text-red-600' : ''
                      }`}
                    >
                      {seg.margin.toFixed(1)}%
                    </td>
                    <td
                      className={`py-2.5 px-2 text-right tabular-nums ${
                        seg.growth < 0 ? 'text-red-600' : 'text-green-600'
                      }`}
                    >
                      {seg.growth > 0 ? '+' : ''}
                      {seg.growth.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-2 text-right font-bold tabular-nums">
                      {seg.riskScore}
                    </td>
                    <td className="py-2.5 px-2 text-center">
                      <Badge variant={seg.riskLevel}>
                        {seg.riskLevel === 'critical'
                          ? '重大'
                          : seg.riskLevel === 'high'
                          ? '高'
                          : seg.riskLevel === 'medium'
                          ? '中'
                          : '低'}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-2 text-right tabular-nums text-muted-foreground">
                      {seg.subsidiaryCount}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
