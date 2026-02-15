'use client'

import { useState, useEffect } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Loader2 } from 'lucide-react'
import { fetchAPI } from '@/lib/api-client'

/** バーの色 (リスクレベルに応じたグラデーション) */
const barColors = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#dc2626']

interface ChartDataItem {
  range: string
  count: number
  label: string
}

/**
 * リスクスコア分布チャート
 * Recharts を使ったバーチャートでリスクスコアの分布を表示
 */
export function RiskChart() {
  const [chartData, setChartData] = useState<ChartDataItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAPI<{ items: Array<{ total_score: number }>; total: number }>('/api/v1/risk-scores/')
      .then((data) => {
        // スコア帯別に集計
        const bins: ChartDataItem[] = [
          { range: '0-20', count: 0, label: '極低リスク' },
          { range: '21-40', count: 0, label: '低リスク' },
          { range: '41-60', count: 0, label: '中リスク' },
          { range: '61-80', count: 0, label: '高リスク' },
          { range: '81-100', count: 0, label: '極高リスク' },
        ]
        for (const item of data.items) {
          const score = item.total_score ?? 0
          if (score <= 20) bins[0].count++
          else if (score <= 40) bins[1].count++
          else if (score <= 60) bins[2].count++
          else if (score <= 80) bins[3].count++
          else bins[4].count++
        }
        setChartData(bins)
      })
      .catch((e) => console.error('Failed to fetch risk scores:', e))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="rounded-xl border border-border bg-card p-6">
      <div className="mb-6">
        <h3 className="text-base font-semibold text-card-foreground">
          リスクスコア分布
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          連結子会社のリスクスコアをスコア帯別に集計
        </p>
      </div>
      <div className="h-72">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                opacity={0.5}
              />
              <XAxis
                dataKey="range"
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--card-foreground))',
                  fontSize: '13px',
                }}
                formatter={(value: number) => [`${value}社`, '']}
                labelFormatter={(label: string) => `スコア帯: ${label}`}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={50}>
                {chartData.map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={barColors[index]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
