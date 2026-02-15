'use client'

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

/** リスクスコア分布のデモデータ */
const mockChartData = [
  { range: '0-20', count: 15, label: '極低リスク' },
  { range: '21-40', count: 13, label: '低リスク' },
  { range: '41-60', count: 10, label: '中リスク' },
  { range: '61-80', count: 8, label: '高リスク' },
  { range: '81-100', count: 4, label: '極高リスク' },
]

/** バーの色 (リスクレベルに応じたグラデーション) */
const barColors = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#dc2626']

/**
 * リスクスコア分布チャート
 * Recharts を使ったバーチャートでリスクスコアの分布を表示
 */
export function RiskChart() {
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
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={mockChartData}
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
              formatter={(value: number, _name: string, props: { payload: { label: string } }) => [
                `${value}社`,
                props.payload.label,
              ]}
              labelFormatter={(label: string) => `スコア帯: ${label}`}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={50}>
              {mockChartData.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={barColors[index]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
