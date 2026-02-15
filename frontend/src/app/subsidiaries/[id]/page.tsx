'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
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
} from 'lucide-react'

/** タブ定義 */
const TABS = [
  { id: 'overview', label: '概要' },
  { id: 'financials', label: '財務データ' },
  { id: 'risk', label: 'リスク分析' },
  { id: 'history', label: '履歴' },
] as const

type TabId = (typeof TABS)[number]['id']

/** モック子会社データ */
const subsidiaryData = {
  id: 'demo-sub-1',
  name: 'グローバルテック・エレクトロニクス株式会社',
  parent: 'グローバルテック株式会社',
  edinetCode: 'E10000',
  securitiesCode: '1000',
  industry: '電気機器',
  country: 'JPN',
  isListed: true,
  riskScore: 72,
  riskLevel: 'high' as const,
  financials: {
    revenue: 45000,
    operatingIncome: 3200,
    netIncome: 2100,
    totalAssets: 85000,
    netAssets: 42000,
    cashFlow: 5600,
    employees: 1250,
    margin: 7.1,
    roe: 5.0,
    debtRatio: 50.6,
  },
}

/** スコアトレンドモック */
const trendData = [
  { period: '2023 Q1', total: 55, da: 48, fraud: 52, rule: 60, benford: 50 },
  { period: '2023 Q2', total: 58, da: 50, fraud: 55, rule: 62, benford: 52 },
  { period: '2023 Q3', total: 62, da: 55, fraud: 58, rule: 65, benford: 55 },
  { period: '2023 Q4', total: 60, da: 52, fraud: 56, rule: 63, benford: 53 },
  { period: '2024 Q1', total: 65, da: 58, fraud: 60, rule: 68, benford: 58 },
  { period: '2024 Q2', total: 68, da: 60, fraud: 65, rule: 70, benford: 60 },
  { period: '2024 Q3', total: 70, da: 62, fraud: 68, rule: 72, benford: 62 },
  { period: '2024 Q4', total: 72, da: 65, fraud: 70, rule: 75, benford: 65 },
]

/** レーダーチャートデータ */
const radarData = [
  { metric: '裁量的発生高', score: 65, fullMark: 100 },
  { metric: '不正指標', score: 70, fullMark: 100 },
  { metric: 'ルールベース', score: 75, fullMark: 100 },
  { metric: 'ベンフォード', score: 65, fullMark: 100 },
  { metric: '関連当事者', score: 55, fullMark: 100 },
  { metric: 'トレンド', score: 60, fullMark: 100 },
]

/** 財務履歴モック */
const financialHistory = [
  { year: 2020, revenue: 35000, income: 2400, assets: 72000 },
  { year: 2021, revenue: 38000, income: 2800, assets: 75000 },
  { year: 2022, revenue: 40000, income: 2600, assets: 78000 },
  { year: 2023, revenue: 42000, income: 2900, assets: 82000 },
  { year: 2024, revenue: 45000, income: 3200, assets: 85000 },
]

/** リスク所見モック */
const riskFindings = [
  {
    id: '1',
    probe: '異常値検出',
    severity: 'high' as const,
    description: '売上高成長率が前年比15.2%と業界平均(5.3%)を大幅に上回っています',
    confidence: 0.82,
  },
  {
    id: '2',
    probe: '財務比率',
    severity: 'medium' as const,
    description: '負債比率が50.6%で業界平均(38.2%)を上回る傾向',
    confidence: 0.75,
  },
  {
    id: '3',
    probe: 'ベンフォード分析',
    severity: 'high' as const,
    description: '売掛金の金額分布がベンフォードの法則から有意に逸脱',
    confidence: 0.88,
  },
  {
    id: '4',
    probe: 'トレンド分析',
    severity: 'medium' as const,
    description: 'リスクスコアが4四半期連続で上昇傾向',
    confidence: 0.70,
  },
]

/**
 * S03: 子会社詳細ページ
 * 個別子会社の詳細情報を4つのタブで表示
 */
export default function SubsidiaryDetailPage() {
  const params = useParams()
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const sub = subsidiaryData

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">{sub.name}</h1>
            <Badge variant={sub.riskLevel}>
              {sub.riskLevel === 'critical'
                ? '重大'
                : sub.riskLevel === 'high'
                ? '高リスク'
                : sub.riskLevel === 'medium'
                ? '中リスク'
                : '低リスク'}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            親会社: {sub.parent} | {sub.industry} | EDINET: {sub.edinetCode}
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-foreground">{sub.riskScore}</p>
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

      {/* タブコンテンツ */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <KPICard
              title="売上高"
              value={sub.financials.revenue.toLocaleString()}
              suffix="百万円"
              delta={7.1}
              icon={<TrendingUp className="w-5 h-5" />}
            />
            <KPICard
              title="営業利益"
              value={sub.financials.operatingIncome.toLocaleString()}
              suffix="百万円"
              delta={10.3}
              icon={<Building2 className="w-5 h-5" />}
            />
            <KPICard
              title="営業利益率"
              value={`${sub.financials.margin}`}
              suffix="%"
              delta={0.5}
              icon={<TrendingUp className="w-5 h-5" />}
            />
            <KPICard
              title="リスク所見"
              value={riskFindings.length}
              suffix="件"
              delta={25}
              invertDelta
              icon={<AlertTriangle className="w-5 h-5" />}
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
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trendData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
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
                      <Line type="monotone" dataKey="da" name="DA" stroke="#f97316" strokeWidth={1} dot={false} />
                      <Line type="monotone" dataKey="fraud" name="不正" stroke="#eab308" strokeWidth={1} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
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
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'financials' && (
        <div className="space-y-6">
          {/* 財務指標テーブル */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">主要財務指標</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: '売上高', value: `${sub.financials.revenue.toLocaleString()} 百万円` },
                  { label: '営業利益', value: `${sub.financials.operatingIncome.toLocaleString()} 百万円` },
                  { label: '純利益', value: `${sub.financials.netIncome.toLocaleString()} 百万円` },
                  { label: '総資産', value: `${sub.financials.totalAssets.toLocaleString()} 百万円` },
                  { label: '純資産', value: `${sub.financials.netAssets.toLocaleString()} 百万円` },
                  { label: '営業CF', value: `${sub.financials.cashFlow.toLocaleString()} 百万円` },
                  { label: 'ROE', value: `${sub.financials.roe}%` },
                  { label: '負債比率', value: `${sub.financials.debtRatio}%` },
                ].map((item) => (
                  <div key={item.label} className="p-3 rounded-lg bg-muted/50">
                    <p className="text-xs text-muted-foreground">{item.label}</p>
                    <p className="mt-1 text-sm font-semibold text-foreground">{item.value}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 財務推移 */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">財務データ推移</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={financialHistory} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--card))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Line type="monotone" dataKey="revenue" name="売上高" stroke="#3b82f6" strokeWidth={2} />
                    <Line type="monotone" dataKey="income" name="営業利益" stroke="#22c55e" strokeWidth={2} />
                    <Line type="monotone" dataKey="assets" name="総資産" stroke="#8b5cf6" strokeWidth={1} strokeDasharray="5 5" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'risk' && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">リスク所見一覧</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {riskFindings.map((finding) => (
                  <div
                    key={finding.id}
                    className="p-4 rounded-lg border border-border hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={finding.severity}>
                          {finding.severity === 'high' ? '高' : '中'}
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
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'history' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">分析履歴</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { date: '2024-12-15', type: '定期分析', score: 72, analyst: 'AI自動' },
                { date: '2024-09-15', type: '定期分析', score: 70, analyst: 'AI自動' },
                { date: '2024-06-15', type: '定期分析', score: 68, analyst: 'AI自動' },
                { date: '2024-03-15', type: '定期分析', score: 65, analyst: 'AI自動' },
                { date: '2023-12-15', type: '定期分析', score: 60, analyst: 'AI自動' },
              ].map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between py-2 border-b border-border last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm text-foreground">{entry.type}</p>
                      <p className="text-xs text-muted-foreground">{entry.date}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold">{entry.score}</span>
                    <span className="text-xs text-muted-foreground">{entry.analyst}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
