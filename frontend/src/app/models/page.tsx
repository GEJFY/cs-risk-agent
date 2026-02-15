'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/KPICard'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  LineChart,
  Line,
} from 'recharts'
import { Brain, Cpu, Zap, Target } from 'lucide-react'

/** モデル定義 */
const models = [
  {
    id: 'da',
    name: '裁量的発生高 (DA)',
    description: '修正ジョーンズモデルに基づく裁量的発生高の推定',
    accuracy: 0.87,
    precision: 0.82,
    recall: 0.91,
    f1: 0.86,
    auc: 0.92,
    status: 'active' as const,
    lastUpdated: '2024-12-01',
  },
  {
    id: 'fraud',
    name: '不正指標 (F-Score)',
    description: 'Dechow et al. F-Scoreモデルによる不正可能性の評価',
    accuracy: 0.84,
    precision: 0.79,
    recall: 0.88,
    f1: 0.83,
    auc: 0.89,
    status: 'active' as const,
    lastUpdated: '2024-12-01',
  },
  {
    id: 'rule',
    name: 'ルールベース',
    description: '監査基準に基づくルールベースのリスク検出',
    accuracy: 0.91,
    precision: 0.88,
    recall: 0.85,
    f1: 0.87,
    auc: 0.94,
    status: 'active' as const,
    lastUpdated: '2024-12-01',
  },
  {
    id: 'benford',
    name: 'ベンフォード分析',
    description: 'ベンフォードの法則に基づく数値分布の異常検出',
    accuracy: 0.78,
    precision: 0.73,
    recall: 0.82,
    f1: 0.77,
    auc: 0.85,
    status: 'active' as const,
    lastUpdated: '2024-12-01',
  },
]

/** モデル比較データ */
const comparisonData = [
  { metric: '精度', DA: 87, FScore: 84, Rule: 91, Benford: 78 },
  { metric: '適合率', DA: 82, FScore: 79, Rule: 88, Benford: 73 },
  { metric: '再現率', DA: 91, FScore: 88, Rule: 85, Benford: 82 },
  { metric: 'F1スコア', DA: 86, FScore: 83, Rule: 87, Benford: 77 },
  { metric: 'AUC', DA: 92, FScore: 89, Rule: 94, Benford: 85 },
]

/** パフォーマンス推移データ */
const performanceHistory = [
  { period: '2024 Q1', da: 85, fraud: 82, rule: 89, benford: 76 },
  { period: '2024 Q2', da: 86, fraud: 83, rule: 90, benford: 77 },
  { period: '2024 Q3', da: 86, fraud: 84, rule: 90, benford: 78 },
  { period: '2024 Q4', da: 87, fraud: 84, rule: 91, benford: 78 },
]

/** レーダーチャートデータ */
const radarData = models.map((m) => ({
  model: m.name.split('(')[0].trim(),
  accuracy: m.accuracy * 100,
  precision: m.precision * 100,
  recall: m.recall * 100,
  f1: m.f1 * 100,
  auc: m.auc * 100,
}))

const radarMetrics = [
  { key: 'accuracy', label: '精度' },
  { key: 'precision', label: '適合率' },
  { key: 'recall', label: '再現率' },
  { key: 'f1', label: 'F1' },
  { key: 'auc', label: 'AUC' },
]

/** モデルカラー */
const MODEL_COLORS: Record<string, string> = {
  DA: '#3b82f6',
  FScore: '#f97316',
  Rule: '#22c55e',
  Benford: '#8b5cf6',
}

/**
 * S04: モデル分析ページ
 * 各分析モデルのパフォーマンス指標と比較を表示
 */
export default function ModelsPage() {
  const avgAccuracy =
    models.reduce((sum, m) => sum + m.accuracy, 0) / models.length
  const avgF1 = models.reduce((sum, m) => sum + m.f1, 0) / models.length
  const avgAuc = models.reduce((sum, m) => sum + m.auc, 0) / models.length

  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">モデル分析</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          各リスク分析モデルのパフォーマンス指標と比較分析
        </p>
      </div>

      {/* KPIカード */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="アクティブモデル"
          value={models.length}
          suffix="個"
          icon={<Brain className="w-5 h-5" />}
        />
        <KPICard
          title="平均精度"
          value={`${(avgAccuracy * 100).toFixed(1)}`}
          suffix="%"
          delta={1.5}
          icon={<Target className="w-5 h-5" />}
        />
        <KPICard
          title="平均F1スコア"
          value={`${(avgF1 * 100).toFixed(1)}`}
          suffix="%"
          delta={0.8}
          icon={<Zap className="w-5 h-5" />}
        />
        <KPICard
          title="平均AUC"
          value={`${(avgAuc * 100).toFixed(1)}`}
          suffix="%"
          delta={1.2}
          icon={<Cpu className="w-5 h-5" />}
        />
      </div>

      {/* モデル比較チャート */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 棒グラフ比較 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">モデル性能比較</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={comparisonData}
                  margin={{ top: 10, right: 20, bottom: 5, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    opacity={0.5}
                  />
                  <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  <YAxis domain={[60, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="DA" name="DA" fill={MODEL_COLORS.DA} radius={[2, 2, 0, 0]} />
                  <Bar dataKey="FScore" name="F-Score" fill={MODEL_COLORS.FScore} radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Rule" name="ルール" fill={MODEL_COLORS.Rule} radius={[2, 2, 0, 0]} />
                  <Bar dataKey="Benford" name="ベンフォード" fill={MODEL_COLORS.Benford} radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* パフォーマンス推移 */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">精度推移</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={performanceHistory}
                  margin={{ top: 10, right: 20, bottom: 5, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="hsl(var(--border))"
                    opacity={0.5}
                  />
                  <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                  <YAxis domain={[70, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Line type="monotone" dataKey="da" name="DA" stroke={MODEL_COLORS.DA} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="fraud" name="F-Score" stroke={MODEL_COLORS.FScore} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="rule" name="ルール" stroke={MODEL_COLORS.Rule} strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="benford" name="ベンフォード" stroke={MODEL_COLORS.Benford} strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* モデル詳細カード */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {models.map((model) => (
          <Card key={model.id} className="hover:shadow-md transition-shadow">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-foreground">{model.name}</h3>
                    <Badge variant="low">Active</Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {model.description}
                  </p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-5 gap-2">
                {[
                  { label: '精度', value: model.accuracy },
                  { label: '適合率', value: model.precision },
                  { label: '再現率', value: model.recall },
                  { label: 'F1', value: model.f1 },
                  { label: 'AUC', value: model.auc },
                ].map((metric) => (
                  <div key={metric.label} className="text-center">
                    <p className="text-[10px] text-muted-foreground">
                      {metric.label}
                    </p>
                    <p className="text-lg font-bold text-foreground">
                      {(metric.value * 100).toFixed(0)}
                    </p>
                    <div className="mt-1 h-1 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary rounded-full"
                        style={{ width: `${metric.value * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <p className="mt-3 text-[10px] text-muted-foreground">
                最終更新: {model.lastUpdated}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
