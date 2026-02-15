'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { Loader2, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'
import { fetchAPI } from '@/lib/api-client'

// 色定義
const COLORS = {
  revenue: '#3b82f6',
  cogs: '#ef4444',
  sga: '#f97316',
  operatingIncome: '#22c55e',
  netIncome: '#8b5cf6',
  totalAssets: '#6366f1',
  totalLiabilities: '#ef4444',
  totalEquity: '#22c55e',
  currentAssets: '#3b82f6',
  ppe: '#f59e0b',
  longTermDebt: '#dc2626',
  ocf: '#06b6d4',
}

const PIE_COLORS = ['#3b82f6', '#22c55e', '#f97316', '#8b5cf6', '#ef4444', '#06b6d4']

interface EntityOption {
  id: string
  name: string
  risk_level?: string
  total_score?: number
}

interface FinancialTrend {
  period: string
  revenue: number
  cogs: number
  sga: number
  operating_income: number
  net_income: number
  total_assets: number
  current_assets: number
  receivables: number
  inventory: number
  total_liabilities: number
  total_equity: number
  long_term_debt: number
  operating_cash_flow: number
}

interface RatioData {
  period: string
  gross_margin: number
  operating_margin: number
  net_margin: number
  roe: number
  roa: number
  current_ratio: number
  debt_equity_ratio: number
  asset_turnover: number
  receivables_turnover: number
  inventory_turnover: number
  ocf_to_revenue: number
}

interface TBAccount {
  account_code: string
  account_name: string
  total_debit: number
  total_credit: number
  balance: number
  entry_count: number
}

interface JournalEntry {
  id: string
  date: string
  account_code: string
  account_name: string
  debit: number
  credit: number
  description: string
  posted_by: string
  is_anomaly: boolean
  anomaly_type: string
}

type TabId = 'overview' | 'pl' | 'bs' | 'ratios' | 'tb' | 'journal'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: '概要' },
  { id: 'pl', label: '損益計算書' },
  { id: 'bs', label: '貸借対照表' },
  { id: 'ratios', label: '財務指標' },
  { id: 'tb', label: '試算表(TB)' },
  { id: 'journal', label: '仕訳一覧' },
]

/**
 * 財務分析ダッシュボード
 * 財務指標・TB推移の可視化、ルールベース/Agent洞察用データ
 */
export default function FinancialsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [entities, setEntities] = useState<EntityOption[]>([])
  const [selectedEntity, setSelectedEntity] = useState<string>('')
  const [trends, setTrends] = useState<FinancialTrend[]>([])
  const [ratios, setRatios] = useState<RatioData[]>([])
  const [tbAccounts, setTbAccounts] = useState<TBAccount[]>([])
  const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([])
  const [anomalyOnly, setAnomalyOnly] = useState(false)
  const [loading, setLoading] = useState(true)
  const [entityName, setEntityName] = useState('')

  // エンティティ一覧取得
  useEffect(() => {
    const load = async () => {
      try {
        const res = await fetchAPI<{ items: EntityOption[] }>(
          '/api/v1/companies/?per_page=50'
        )
        setEntities(res.items)
        if (res.items.length > 0) {
          // 最初の子会社を選択 (親会社でなく)
          const firstSub = res.items.find((e) => e.id.startsWith('SUB-')) || res.items[0]
          setSelectedEntity(firstSub.id)
        }
      } catch {
        // fallback
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  // 選択エンティティのデータ取得
  useEffect(() => {
    if (!selectedEntity) return

    const loadEntityData = async () => {
      setLoading(true)
      try {
        const [trendRes, ratioRes, tbRes, jeRes] = await Promise.all([
          fetchAPI<{ entity_name: string; trends: FinancialTrend[] }>(
            `/api/v1/financials/statements/${selectedEntity}/trend`
          ),
          fetchAPI<{ ratios: RatioData[] }>(
            `/api/v1/financials/ratios/${selectedEntity}`
          ),
          fetchAPI<{ entity_name: string; accounts: TBAccount[] }>(
            `/api/v1/financials/trial-balance/${selectedEntity}`
          ),
          fetchAPI<{ items: JournalEntry[] }>(
            `/api/v1/financials/journal-entries/${selectedEntity}?anomaly_only=${anomalyOnly}&limit=200`
          ),
        ])
        setTrends(trendRes.trends)
        setEntityName(trendRes.entity_name)
        setRatios(ratioRes.ratios)
        setTbAccounts(tbRes.accounts)
        setJournalEntries(jeRes.items)
      } catch {
        // error
      } finally {
        setLoading(false)
      }
    }
    loadEntityData()
  }, [selectedEntity, anomalyOnly])

  const latestTrend = trends.length > 0 ? trends[trends.length - 1] : null

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">財務分析ダッシュボード</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            財務指標・TB推移・仕訳分析 — ルールベースエンジン / AIエージェント連携
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedEntity}
            onChange={(e) => setSelectedEntity(e.target.value)}
            className="px-3 py-2 rounded-lg border border-border bg-card text-sm text-foreground"
          >
            {entities.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} {e.total_score ? `(${e.total_score})` : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* タブ */}
      <div className="border-b border-border">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
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

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* ===== 概要タブ ===== */}
          {activeTab === 'overview' && latestTrend && (
            <div className="space-y-6">
              {/* KPI */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KPISimple label="売上高" value={formatNum(latestTrend.revenue)} unit="百万円" icon={<TrendingUp className="w-4 h-4" />} />
                <KPISimple label="営業利益" value={formatNum(latestTrend.operating_income)} unit="百万円" icon={<BarChart3 className="w-4 h-4" />} />
                <KPISimple label="総資産" value={formatNum(latestTrend.total_assets)} unit="百万円" icon={<TrendingUp className="w-4 h-4" />} />
                <KPISimple label="営業CF" value={formatNum(latestTrend.operating_cash_flow)} unit="百万円"
                  icon={latestTrend.operating_cash_flow >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  negative={latestTrend.operating_cash_flow < 0}
                />
              </div>

              {/* 売上・利益推移 + 財務指標レーダー */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">売上・利益推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Line type="monotone" dataKey="revenue" name="売上高" stroke={COLORS.revenue} strokeWidth={2} dot={{ r: 3 }} />
                          <Line type="monotone" dataKey="operating_income" name="営業利益" stroke={COLORS.operatingIncome} strokeWidth={2} dot={{ r: 3 }} />
                          <Line type="monotone" dataKey="net_income" name="純利益" stroke={COLORS.netIncome} strokeWidth={1} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">財務指標レーダー（最新四半期）</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      {ratios.length > 0 && (
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart data={makeRadarData(ratios[ratios.length - 1])}>
                            <PolarGrid stroke="hsl(var(--border))" />
                            <PolarAngleAxis dataKey="metric" tick={{ fontSize: 9 }} />
                            <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 8 }} />
                            <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} strokeWidth={2} />
                          </RadarChart>
                        </ResponsiveContainer>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* BS構成 + CF */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">資産・負債・純資産の推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Bar dataKey="total_assets" name="総資産" fill={COLORS.totalAssets} opacity={0.7} />
                          <Bar dataKey="total_liabilities" name="負債" fill={COLORS.totalLiabilities} opacity={0.7} />
                          <Bar dataKey="total_equity" name="純資産" fill={COLORS.totalEquity} opacity={0.7} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">営業CFと純利益の対比</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Bar dataKey="operating_cash_flow" name="営業CF" fill={COLORS.ocf} />
                          <Bar dataKey="net_income" name="純利益" fill={COLORS.netIncome} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* ===== 損益計算書タブ ===== */}
          {activeTab === 'pl' && (
            <div className="space-y-6">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">PL推移 — {entityName}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                        <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        <Bar dataKey="revenue" name="売上高" fill={COLORS.revenue} />
                        <Bar dataKey="cogs" name="売上原価" fill={COLORS.cogs} opacity={0.6} />
                        <Bar dataKey="sga" name="販管費" fill={COLORS.sga} opacity={0.6} />
                        <Bar dataKey="operating_income" name="営業利益" fill={COLORS.operatingIncome} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">マージン推移 (%)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={ratios} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                        <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Legend wrapperStyle={{ fontSize: 11 }} />
                        <Line type="monotone" dataKey="gross_margin" name="売上総利益率" stroke="#3b82f6" strokeWidth={2} />
                        <Line type="monotone" dataKey="operating_margin" name="営業利益率" stroke="#22c55e" strokeWidth={2} />
                        <Line type="monotone" dataKey="net_margin" name="純利益率" stroke="#8b5cf6" strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* ===== 貸借対照表タブ ===== */}
          {activeTab === 'bs' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">資産構成推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Bar dataKey="receivables" name="売掛金" stackId="assets" fill="#3b82f6" />
                          <Bar dataKey="inventory" name="棚卸資産" stackId="assets" fill="#f97316" />
                          <Bar dataKey="current_assets" name="流動資産(他)" stackId="assets" fill="#06b6d4" opacity={0.4} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">負債・資本構成推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={trends} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Bar dataKey="total_liabilities" name="負債合計" stackId="lq" fill={COLORS.totalLiabilities} opacity={0.7} />
                          <Bar dataKey="total_equity" name="純資産" stackId="lq" fill={COLORS.totalEquity} opacity={0.7} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 最新BS構成 円グラフ */}
              {latestTrend && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">資産構成（最新四半期）</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[280px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={[
                                { name: '売掛金', value: latestTrend.receivables },
                                { name: '棚卸資産', value: latestTrend.inventory },
                                { name: '流動資産(他)', value: Math.max(latestTrend.current_assets - latestTrend.receivables - latestTrend.inventory, 0) },
                                { name: '固定資産', value: Math.max(latestTrend.total_assets - latestTrend.current_assets, 0) },
                              ]}
                              dataKey="value"
                              cx="50%" cy="50%" outerRadius={100} label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            >
                              {PIE_COLORS.map((c, i) => <Cell key={i} fill={c} />)}
                            </Pie>
                            <Tooltip contentStyle={tooltipStyle} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">負債・純資産構成（最新四半期）</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[280px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={[
                                { name: '流動負債', value: latestTrend.total_liabilities - latestTrend.long_term_debt },
                                { name: '長期借入金', value: latestTrend.long_term_debt },
                                { name: '純資産', value: latestTrend.total_equity },
                              ]}
                              dataKey="value"
                              cx="50%" cy="50%" outerRadius={100} label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
                            >
                              <Cell fill="#ef4444" />
                              <Cell fill="#f97316" />
                              <Cell fill="#22c55e" />
                            </Pie>
                            <Tooltip contentStyle={tooltipStyle} />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          )}

          {/* ===== 財務指標タブ ===== */}
          {activeTab === 'ratios' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">収益性指標推移 (ROE/ROA)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={ratios} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Line type="monotone" dataKey="roe" name="ROE (%)" stroke="#3b82f6" strokeWidth={2} />
                          <Line type="monotone" dataKey="roa" name="ROA (%)" stroke="#22c55e" strokeWidth={2} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">安全性指標推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={ratios} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Line type="monotone" dataKey="current_ratio" name="流動比率" stroke="#3b82f6" strokeWidth={2} />
                          <Line type="monotone" dataKey="debt_equity_ratio" name="D/Eレシオ" stroke="#ef4444" strokeWidth={2} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">効率性指標推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={ratios} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Legend wrapperStyle={{ fontSize: 11 }} />
                          <Line type="monotone" dataKey="asset_turnover" name="総資産回転率" stroke="#8b5cf6" strokeWidth={2} />
                          <Line type="monotone" dataKey="receivables_turnover" name="売掛金回転率" stroke="#f97316" strokeWidth={2} />
                          <Line type="monotone" dataKey="inventory_turnover" name="棚卸資産回転率" stroke="#06b6d4" strokeWidth={2} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">営業CF/売上高比率推移</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[280px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={ratios} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                          <XAxis dataKey="period" tick={{ fontSize: 10 }} />
                          <YAxis tick={{ fontSize: 10 }} />
                          <Tooltip contentStyle={tooltipStyle} />
                          <Bar dataKey="ocf_to_revenue" name="OCF/売上高 (%)" fill={COLORS.ocf} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 最新指標テーブル */}
              {ratios.length > 0 && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">最新四半期 財務指標一覧</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                      {Object.entries({
                        '売上総利益率': `${ratios[ratios.length - 1].gross_margin}%`,
                        '営業利益率': `${ratios[ratios.length - 1].operating_margin}%`,
                        '純利益率': `${ratios[ratios.length - 1].net_margin}%`,
                        'ROE': `${ratios[ratios.length - 1].roe}%`,
                        'ROA': `${ratios[ratios.length - 1].roa}%`,
                        '流動比率': `${ratios[ratios.length - 1].current_ratio}x`,
                        'D/Eレシオ': `${ratios[ratios.length - 1].debt_equity_ratio}x`,
                        '総資産回転率': `${ratios[ratios.length - 1].asset_turnover}x`,
                        '売掛金回転率': `${ratios[ratios.length - 1].receivables_turnover}x`,
                        '棚卸回転率': `${ratios[ratios.length - 1].inventory_turnover}x`,
                        'OCF/売上高': `${ratios[ratios.length - 1].ocf_to_revenue}%`,
                      }).map(([label, value]) => (
                        <div key={label} className="p-3 rounded-lg bg-muted/50">
                          <p className="text-xs text-muted-foreground">{label}</p>
                          <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* ===== 試算表タブ ===== */}
          {activeTab === 'tb' && (
            <div className="space-y-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">
                    試算表 (Trial Balance) — {entityName}
                    <span className="ml-2 text-xs text-muted-foreground font-normal">
                      {tbAccounts.length} 勘定科目
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left py-2 px-3 font-medium text-muted-foreground">勘定コード</th>
                          <th className="text-left py-2 px-3 font-medium text-muted-foreground">勘定科目</th>
                          <th className="text-right py-2 px-3 font-medium text-muted-foreground">借方合計</th>
                          <th className="text-right py-2 px-3 font-medium text-muted-foreground">貸方合計</th>
                          <th className="text-right py-2 px-3 font-medium text-muted-foreground">残高</th>
                          <th className="text-right py-2 px-3 font-medium text-muted-foreground">仕訳数</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tbAccounts.map((acc) => (
                          <tr key={acc.account_code} className="border-b border-border/50 hover:bg-muted/30">
                            <td className="py-2 px-3 font-mono text-xs">{acc.account_code}</td>
                            <td className="py-2 px-3">{acc.account_name}</td>
                            <td className="py-2 px-3 text-right font-mono">{formatNum(acc.total_debit)}</td>
                            <td className="py-2 px-3 text-right font-mono">{formatNum(acc.total_credit)}</td>
                            <td className={`py-2 px-3 text-right font-mono font-semibold ${acc.balance < 0 ? 'text-red-500' : ''}`}>
                              {formatNum(acc.balance)}
                            </td>
                            <td className="py-2 px-3 text-right">{acc.entry_count}</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot>
                        <tr className="border-t-2 border-border font-semibold">
                          <td colSpan={2} className="py-2 px-3">合計</td>
                          <td className="py-2 px-3 text-right font-mono">
                            {formatNum(tbAccounts.reduce((s, a) => s + a.total_debit, 0))}
                          </td>
                          <td className="py-2 px-3 text-right font-mono">
                            {formatNum(tbAccounts.reduce((s, a) => s + a.total_credit, 0))}
                          </td>
                          <td className="py-2 px-3 text-right font-mono">
                            {formatNum(tbAccounts.reduce((s, a) => s + a.balance, 0))}
                          </td>
                          <td className="py-2 px-3 text-right">
                            {tbAccounts.reduce((s, a) => s + a.entry_count, 0)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* TB勘定科目別残高チャート */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">勘定科目別残高</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={tbAccounts.filter((a) => Math.abs(a.balance) > 0)}
                        layout="vertical"
                        margin={{ top: 5, right: 20, bottom: 5, left: 80 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
                        <XAxis type="number" tick={{ fontSize: 10 }} />
                        <YAxis type="category" dataKey="account_name" tick={{ fontSize: 10 }} width={80} />
                        <Tooltip contentStyle={tooltipStyle} />
                        <Bar dataKey="balance" name="残高" fill="#3b82f6">
                          {tbAccounts.map((entry, idx) => (
                            <Cell key={idx} fill={entry.balance >= 0 ? '#3b82f6' : '#ef4444'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* ===== 仕訳一覧タブ ===== */}
          {activeTab === 'journal' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={anomalyOnly}
                    onChange={(e) => setAnomalyOnly(e.target.checked)}
                    className="rounded"
                  />
                  異常仕訳のみ表示
                </label>
                <span className="text-xs text-muted-foreground">
                  {journalEntries.length} 件表示
                </span>
              </div>

              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/30">
                          <th className="text-left py-2 px-3 font-medium text-muted-foreground">日付</th>
                          <th className="text-left py-2 px-3 font-medium text-muted-foreground">勘定科目</th>
                          <th className="text-right py-2 px-3 font-medium text-muted-foreground">借方</th>
                          <th className="text-right py-2 px-3 font-medium text-muted-foreground">貸方</th>
                          <th className="text-left py-2 px-3 font-medium text-muted-foreground">摘要</th>
                          <th className="text-left py-2 px-3 font-medium text-muted-foreground">起票者</th>
                          <th className="text-center py-2 px-3 font-medium text-muted-foreground">状態</th>
                        </tr>
                      </thead>
                      <tbody>
                        {journalEntries.map((je) => (
                          <tr
                            key={je.id}
                            className={`border-b border-border/50 hover:bg-muted/30 ${
                              je.is_anomaly ? 'bg-red-50 dark:bg-red-950/20' : ''
                            }`}
                          >
                            <td className="py-2 px-3 text-xs">{je.date}</td>
                            <td className="py-2 px-3">
                              <span className="font-mono text-xs text-muted-foreground mr-1">{je.account_code}</span>
                              {je.account_name}
                            </td>
                            <td className="py-2 px-3 text-right font-mono">
                              {je.debit > 0 ? formatNum(je.debit) : ''}
                            </td>
                            <td className="py-2 px-3 text-right font-mono">
                              {je.credit > 0 ? formatNum(je.credit) : ''}
                            </td>
                            <td className="py-2 px-3 text-xs max-w-[200px] truncate">{je.description}</td>
                            <td className="py-2 px-3 text-xs">{je.posted_by}</td>
                            <td className="py-2 px-3 text-center">
                              {je.is_anomaly ? (
                                <Badge variant="critical" className="text-[10px]">
                                  {je.anomaly_type || '異常'}
                                </Badge>
                              ) : (
                                <span className="text-xs text-muted-foreground">正常</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// --- ヘルパー ---

const tooltipStyle = {
  backgroundColor: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '8px',
  fontSize: '11px',
}

function formatNum(n: number): string {
  if (Math.abs(n) >= 1000) return n.toLocaleString('ja-JP', { maximumFractionDigits: 0 })
  return n.toLocaleString('ja-JP', { maximumFractionDigits: 1 })
}

function KPISimple({
  label, value, unit, icon, negative,
}: {
  label: string; value: string; unit: string; icon: React.ReactNode; negative?: boolean
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className={`text-xl font-bold ${negative ? 'text-red-500' : 'text-foreground'}`}>
              {value} <span className="text-xs font-normal text-muted-foreground">{unit}</span>
            </p>
          </div>
          <div className="p-2 rounded-lg bg-muted text-muted-foreground">{icon}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function makeRadarData(r: RatioData) {
  // 各指標を0-100にスケーリング
  return [
    { metric: '売上総利益率', value: Math.min(Math.max(r.gross_margin, 0), 100) },
    { metric: '営業利益率', value: Math.min(Math.max(r.operating_margin * 2, 0), 100) },
    { metric: 'ROE', value: Math.min(Math.max(r.roe * 3, 0), 100) },
    { metric: '流動比率', value: Math.min(r.current_ratio * 30, 100) },
    { metric: '資産回転率', value: Math.min(r.asset_turnover * 100, 100) },
    { metric: 'OCF/売上高', value: Math.min(Math.max(r.ocf_to_revenue * 2, 0), 100) },
  ]
}
