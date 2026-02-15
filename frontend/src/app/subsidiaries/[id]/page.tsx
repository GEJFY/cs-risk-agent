'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/dashboard/KPICard'
import {
  LineChart,
  Line,
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
} from 'recharts'
import {
  Building2,
  TrendingUp,
  AlertTriangle,
  FileText,
  Loader2,
} from 'lucide-react'
import { fetchAPI } from '@/lib/api-client'

/** タブ定義 */
const TABS = [
  { id: 'overview', label: '概要' },
  { id: 'financials', label: '財務データ' },
  { id: 'risk', label: 'リスク分析' },
  { id: 'history', label: '履歴' },
] as const

type TabId = (typeof TABS)[number]['id']

interface EntityDetail {
  id: string
  name: string
  name_en?: string
  parent_company_id?: string
  country: string
  segment?: string
  ownership_ratio?: number
  description?: string
  is_active?: boolean
  risk_score?: {
    entity_id: string
    entity_name: string
    total_score: number
    risk_level: string
    da_score: number
    fraud_score: number
    rule_score: number
    benford_score: number
    risk_factors: string[]
    analysis_date: string
    fiscal_year: number
    fiscal_quarter: number
  }
}

interface TrendPoint {
  fiscal_year: number
  fiscal_quarter: number
  total_score: number
}

interface Alert {
  id: string
  entity_id: string
  entity_name: string
  severity: string
  category: string
  title: string
  description: string
  created_at: string
  is_read: boolean
  recommended_action?: string
}

/**
 * S03: 子会社詳細ページ
 * APIからデータを取得して4つのタブで表示
 */
export default function SubsidiaryDetailPage() {
  const params = useParams()
  const entityId = params.id as string
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [entity, setEntity] = useState<EntityDetail | null>(null)
  const [trends, setTrends] = useState<TrendPoint[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!entityId) return

    const loadData = async () => {
      setLoading(true)
      setError(null)
      try {
        const [entityRes, trendRes, alertsRes] = await Promise.all([
          fetchAPI<EntityDetail>(`/api/v1/companies/${entityId}`),
          fetchAPI<{ company_id: string; trends: TrendPoint[] }>(
            `/api/v1/analysis/results/${entityId}/trend`
          ),
          fetchAPI<{ items: Alert[]; total: number }>('/api/v1/risk-scores/alerts'),
        ])
        setEntity(entityRes)
        setTrends(trendRes.trends)
        // エンティティに関連するアラートのみフィルタ
        setAlerts(alertsRes.items.filter((a) => a.entity_id === entityId))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'データの取得に失敗しました')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [entityId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        <span className="ml-3 text-muted-foreground">読み込み中...</span>
      </div>
    )
  }

  if (error || !entity) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-destructive">{error || 'エンティティが見つかりません'}</p>
      </div>
    )
  }

  const rs = entity.risk_score
  const riskLevel = rs?.risk_level || 'low'
  const riskScore = rs?.total_score ?? 0

  // レーダーチャートデータ
  const radarData = rs
    ? [
        { metric: '裁量的発生高(DA)', score: rs.da_score, fullMark: 100 },
        { metric: '不正指標(F-Score)', score: rs.fraud_score, fullMark: 100 },
        { metric: 'ルールベース', score: rs.rule_score, fullMark: 100 },
        { metric: 'ベンフォード', score: rs.benford_score, fullMark: 100 },
      ]
    : []

  // トレンドチャートデータ
  const trendChartData = trends.map((t) => ({
    period: `${t.fiscal_year} Q${t.fiscal_quarter}`,
    total: t.total_score,
  }))

  // リスク所見 = risk_factors + alerts
  const riskFindings = [
    ...(rs?.risk_factors || []).map((f, i) => ({
      id: `rf-${i}`,
      probe: 'リスク要因',
      severity: 'high' as const,
      description: f,
      confidence: 0.85,
    })),
    ...alerts.map((a) => ({
      id: a.id,
      probe: a.category,
      severity: a.severity as 'critical' | 'high' | 'medium' | 'low',
      description: a.description,
      confidence: 0.9,
    })),
  ]

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">{entity.name}</h1>
            <Badge variant={riskLevel as 'critical' | 'high' | 'medium' | 'low'}>
              {riskLevel === 'critical'
                ? '重大'
                : riskLevel === 'high'
                ? '高リスク'
                : riskLevel === 'medium'
                ? '中リスク'
                : '低リスク'}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {entity.name_en && `${entity.name_en} | `}
            {entity.segment && `${entity.segment} | `}
            {entity.country}
            {entity.ownership_ratio != null && ` | 持分 ${(entity.ownership_ratio * 100).toFixed(0)}%`}
          </p>
          {entity.description && (
            <p className="mt-1 text-xs text-muted-foreground">{entity.description}</p>
          )}
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-foreground">{riskScore}</p>
          <p className="text-xs text-muted-foreground">リスクスコア</p>
        </div>
      </div>

      {/* タブ */}
      <div className="border-b border-border">
        <div className="flex gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 概要タブ */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="総合リスクスコア"
              value={riskScore}
              suffix="/ 100"
              icon={<TrendingUp className="w-5 h-5" />}
            />
            <KPICard
              title="DA スコア"
              value={rs?.da_score?.toFixed(1) ?? '-'}
              icon={<Building2 className="w-5 h-5" />}
            />
            <KPICard
              title="不正指標スコア"
              value={rs?.fraud_score?.toFixed(1) ?? '-'}
              icon={<AlertTriangle className="w-5 h-5" />}
            />
            <KPICard
              title="リスク所見"
              value={riskFindings.length}
              suffix="件"
              icon={<FileText className="w-5 h-5" />}
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* スコアトレンド */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">リスクスコア推移</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[280px]">
                  {trendChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={trendChartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                        <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            border: '1px solid hsl(var(--border))',
                            borderRadius: '8px',
                            fontSize: '12px',
                          }}
                        />
                        <Line type="monotone" dataKey="total" name="総合" stroke="#dc2626" strokeWidth={2} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-muted-foreground pt-8 text-center">トレンドデータなし</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* レーダーチャート */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">リスクプロファイル</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-[280px]">
                  {radarData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={radarData}>
                        <PolarGrid stroke="hsl(var(--border))" />
                        <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10 }} />
                        <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
                        <Radar
                          dataKey="score"
                          stroke="#dc2626"
                          fill="#dc2626"
                          fillOpacity={0.15}
                          strokeWidth={2}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-muted-foreground pt-8 text-center">リスクスコアなし</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* リスク分析タブ */}
      {activeTab === 'risk' && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">リスク所見一覧 ({riskFindings.length}件)</CardTitle>
            </CardHeader>
            <CardContent>
              {riskFindings.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">リスク所見はありません</p>
              ) : (
                <div className="space-y-3">
                  {riskFindings.map((finding) => (
                    <div
                      key={finding.id}
                      className="p-4 rounded-lg border border-border hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant={finding.severity as 'critical' | 'high' | 'medium' | 'low'}>
                            {finding.severity === 'critical'
                              ? '重大'
                              : finding.severity === 'high'
                              ? '高'
                              : finding.severity === 'medium'
                              ? '中'
                              : '低'}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {finding.probe}
                          </span>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <span>信頼度:</span>
                          <span className="font-medium text-foreground">
                            {(finding.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                      <p className="mt-2 text-sm text-foreground">
                        {finding.description}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* アラート詳細 */}
          {alerts.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">アラート詳細</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="p-4 rounded-lg border border-border"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={alert.severity as 'critical' | 'high' | 'medium' | 'low'}>
                          {alert.severity}
                        </Badge>
                        <span className="text-sm font-medium">{alert.title}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{alert.description}</p>
                      {alert.recommended_action && (
                        <p className="mt-2 text-xs text-blue-600">
                          推奨対応: {alert.recommended_action}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 財務データタブ */}
      {activeTab === 'financials' && (
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">分析スコア詳細</CardTitle>
            </CardHeader>
            <CardContent>
              {rs ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: '総合スコア', value: `${rs.total_score}` },
                    { label: '裁量的発生高 (DA)', value: `${rs.da_score}` },
                    { label: '不正指標 (F-Score)', value: `${rs.fraud_score}` },
                    { label: 'ルールベース', value: `${rs.rule_score}` },
                    { label: 'ベンフォード分析', value: `${rs.benford_score}` },
                    { label: 'リスクレベル', value: rs.risk_level },
                    { label: '分析日', value: rs.analysis_date },
                    { label: '対象期', value: `${rs.fiscal_year} Q${rs.fiscal_quarter}` },
                  ].map((item) => (
                    <div key={item.label} className="p-3 rounded-lg bg-muted/50">
                      <p className="text-xs text-muted-foreground">{item.label}</p>
                      <p className="mt-1 text-sm font-semibold text-foreground">{item.value}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground py-4 text-center">スコアデータなし</p>
              )}
            </CardContent>
          </Card>

          {/* スコア推移 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">スコア推移</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                {trendChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendChartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                      <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                      <Line type="monotone" dataKey="total" name="総合スコア" stroke="#dc2626" strokeWidth={2} dot={{ r: 4 }} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-sm text-muted-foreground pt-8 text-center">トレンドデータなし</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 履歴タブ */}
      {activeTab === 'history' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">分析履歴</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {trends.length > 0 ? (
                trends.map((t, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between py-2 border-b border-border last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                      <div>
                        <p className="text-sm text-foreground">定期分析</p>
                        <p className="text-xs text-muted-foreground">
                          {t.fiscal_year}年 Q{t.fiscal_quarter}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold">{t.total_score}</span>
                      <span className="text-xs text-muted-foreground">AI自動</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-muted-foreground py-4 text-center">分析履歴はありません</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
