'use client'

import { useState } from 'react'
import { ChatInterface } from '@/components/ai/ChatInterface'
import { InsightCard, type Insight } from '@/components/ai/InsightCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Brain, Filter, RefreshCw } from 'lucide-react'

/** モックインサイトデータ */
const mockInsights: Insight[] = [
  {
    id: '1',
    title: '売上高の異常成長パターン検出',
    description:
      'グローバルテック株式会社の売上高が前年比150%と異常に高い成長率を示しています。同業種の平均成長率(5.3%)と大幅に乖離しており、収益認識の適切性について詳細な調査が推奨されます。',
    severity: 'critical',
    category: '異常値検出',
    confidence: 0.92,
    evidence: [
      '売上高成長率: 150% (業界平均: 5.3%)',
      'Zスコア: 4.2 (閾値: 3.0)',
      '新規顧客による売上が全体の65%',
    ],
    recommendation:
      '四半期別の売上明細を確認し、特に期末月の売上集中パターンがないか精査してください。',
  },
  {
    id: '2',
    title: '流動性リスクの悪化傾向',
    description:
      '横浜バイオ株式会社の流動比率が4四半期連続で低下しています。現在の流動比率(0.85)は業界基準(1.2)を大幅に下回っており、短期的な資金繰りリスクが懸念されます。',
    severity: 'high',
    category: '財務比率分析',
    confidence: 0.88,
    evidence: [
      '流動比率: 0.85 (業界基準: 1.2)',
      '4四半期連続の低下トレンド',
      '短期借入金が前年比42%増',
    ],
    recommendation:
      '資金繰り計画と短期借入金の返済スケジュールを確認し、必要に応じて資金調達計画の策定を検討してください。',
  },
  {
    id: '3',
    title: 'ベンフォード分析での逸脱検出',
    description:
      '大阪製薬株式会社の売掛金の金額分布がベンフォードの法則から統計的に有意な逸脱を示しています。特に先頭数字「1」と「9」の出現頻度が理論値と大きく異なります。',
    severity: 'high',
    category: 'ベンフォード分析',
    confidence: 0.85,
    evidence: [
      'カイ二乗検定 p値: 0.003',
      '先頭数字「1」: 観測18.2% vs 理論30.1%',
      '先頭数字「9」: 観測12.8% vs 理論4.6%',
    ],
    recommendation:
      '売掛金の個別明細を確認し、端数処理や丸め処理が適切に行われているか確認してください。',
  },
  {
    id: '4',
    title: '関連当事者取引の増加',
    description:
      '名古屋重工株式会社の関連当事者取引が前年比32%増加しています。特に子会社間取引の価格設定について移転価格の適切性を確認する必要があります。',
    severity: 'medium',
    category: '関連当事者分析',
    confidence: 0.75,
    evidence: [
      '関連当事者取引額: 前年比32%増',
      '子会社間取引比率: 全体の28%',
      '海外子会社との取引が55%',
    ],
    recommendation:
      '移転価格ドキュメンテーションの整備状況を確認し、独立企業間価格との比較分析を実施してください。',
  },
  {
    id: '5',
    title: '業種全体のリスクスコア上昇',
    description:
      '電気機器セクター全体でリスクスコアが前四半期比で平均4.2ポイント上昇しています。半導体不足の解消に伴う在庫調整リスクと、為替変動の影響が主因と推定されます。',
    severity: 'medium',
    category: 'トレンド分析',
    confidence: 0.72,
    evidence: [
      '電気機器セクター平均スコア: 52.3 (+4.2)',
      '在庫回転率の低下: 平均12%',
      '為替影響: 円安進行による評価損リスク',
    ],
  },
  {
    id: '6',
    title: 'クロスリファレンス：複合リスク確認',
    description:
      'グローバルテック株式会社について、異常値検出・不正指標・ベンフォード分析の3つのプローブで高リスク所見が検出されました。複数手法での裏付けにより、信頼度が高い評価となっています。',
    severity: 'critical',
    category: 'クロスリファレンス',
    confidence: 0.95,
    evidence: [
      '3つの独立したプローブで高リスク検出',
      '異常値検出: Zスコア 4.2',
      '不正指標: F-Score 2.8 (閾値 2.0)',
      'ベンフォード: 有意な逸脱あり',
    ],
    recommendation:
      '特別監査チームの派遣を検討し、経営者インタビューと主要取引先への確認手続きを実施してください。',
  },
]

/** 重大度フィルター */
const SEVERITY_FILTERS = [
  { value: 'all', label: 'すべて' },
  { value: 'critical', label: '重大' },
  { value: 'high', label: '高' },
  { value: 'medium', label: '中' },
  { value: 'low', label: '低' },
]

/**
 * S05: AI インサイトページ
 * AIによる分析インサイトの表示とチャットインターフェース
 */
export default function InsightsPage() {
  const [severityFilter, setSeverityFilter] = useState('all')

  const filteredInsights =
    severityFilter === 'all'
      ? mockInsights
      : mockInsights.filter((i) => i.severity === severityFilter)

  const criticalCount = mockInsights.filter(
    (i) => i.severity === 'critical'
  ).length
  const highCount = mockInsights.filter((i) => i.severity === 'high').length

  return (
    <div className="space-y-6">
      {/* ページヘッダー */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Brain className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold text-foreground">
              AI インサイト
            </h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            AIが検出したリスク所見と分析結果
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="critical">{criticalCount} 重大</Badge>
          <Badge variant="high">{highCount} 高リスク</Badge>
          <Badge variant="secondary">
            {mockInsights.length} 件のインサイト
          </Badge>
        </div>
      </div>

      {/* メインレイアウト */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* インサイトリスト */}
        <div className="lg:col-span-2 space-y-4">
          {/* フィルターバー */}
          <Card>
            <CardContent className="py-3 px-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    フィルター:
                  </span>
                  <div className="flex gap-1">
                    {SEVERITY_FILTERS.map((filter) => (
                      <button
                        key={filter.value}
                        onClick={() => setSeverityFilter(filter.value)}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                          severityFilter === filter.value
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                </div>
                <Button variant="ghost" size="sm" className="text-xs">
                  <RefreshCw className="w-3 h-3 mr-1" />
                  更新
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* インサイトカード一覧 */}
          <div className="space-y-3">
            {filteredInsights.map((insight) => (
              <InsightCard key={insight.id} insight={insight} />
            ))}

            {filteredInsights.length === 0 && (
              <Card>
                <CardContent className="py-12 text-center">
                  <p className="text-sm text-muted-foreground">
                    該当するインサイトがありません
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* チャットインターフェース */}
        <div className="lg:col-span-1">
          <div className="sticky top-6">
            <ChatInterface
              title="リスク分析 AI"
              tier="cost_effective"
              className="h-[calc(100vh-12rem)]"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
