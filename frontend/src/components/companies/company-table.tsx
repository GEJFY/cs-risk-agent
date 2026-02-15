'use client'

import { useState } from 'react'
import {
  ArrowUpDown,
  ExternalLink,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
} from 'lucide-react'
import type { Company, RiskLevel } from '@/types'

/** デモ用企業データ */
const mockCompanies: Company[] = [
  {
    id: 'c-001',
    name: '東南アジア製造子会社',
    nameEn: 'Southeast Asia Manufacturing Co.',
    country: 'タイ',
    region: 'APAC',
    ownershipPct: 100,
    consolidationType: 'full',
    industry: '製造業',
    fiscalYearEnd: '3月',
    lastAnalysisDate: '2026-02-10',
    riskScore: 87,
    riskLevel: 'critical',
  },
  {
    id: 'c-002',
    name: '欧州販売子会社',
    nameEn: 'Europe Sales GmbH',
    country: 'ドイツ',
    region: 'EMEA',
    ownershipPct: 100,
    consolidationType: 'full',
    industry: '卸売業',
    fiscalYearEnd: '12月',
    lastAnalysisDate: '2026-02-08',
    riskScore: 72,
    riskLevel: 'high',
  },
  {
    id: 'c-003',
    name: '北米IT子会社',
    nameEn: 'North America IT Inc.',
    country: 'アメリカ',
    region: 'Americas',
    ownershipPct: 80,
    consolidationType: 'full',
    industry: '情報通信業',
    fiscalYearEnd: '12月',
    lastAnalysisDate: '2026-02-12',
    riskScore: 55,
    riskLevel: 'medium',
  },
  {
    id: 'c-004',
    name: '中国物流子会社',
    nameEn: 'China Logistics Co., Ltd.',
    country: '中国',
    region: 'APAC',
    ownershipPct: 70,
    consolidationType: 'full',
    industry: '運輸業',
    fiscalYearEnd: '12月',
    lastAnalysisDate: '2026-02-05',
    riskScore: 68,
    riskLevel: 'high',
  },
  {
    id: 'c-005',
    name: 'インド開発子会社',
    nameEn: 'India Development Pvt. Ltd.',
    country: 'インド',
    region: 'APAC',
    ownershipPct: 100,
    consolidationType: 'full',
    industry: '情報通信業',
    fiscalYearEnd: '3月',
    lastAnalysisDate: '2026-02-14',
    riskScore: 25,
    riskLevel: 'low',
  },
  {
    id: 'c-006',
    name: 'ブラジル資源子会社',
    nameEn: 'Brazil Resources Ltda.',
    country: 'ブラジル',
    region: 'Americas',
    ownershipPct: 60,
    consolidationType: 'full',
    industry: '鉱業',
    fiscalYearEnd: '12月',
    lastAnalysisDate: '2026-01-28',
    riskScore: 83,
    riskLevel: 'critical',
  },
  {
    id: 'c-007',
    name: '韓国電子部品子会社',
    nameEn: 'Korea Electronics Co., Ltd.',
    country: '韓国',
    region: 'APAC',
    ownershipPct: 51,
    consolidationType: 'full',
    industry: '製造業',
    fiscalYearEnd: '12月',
    lastAnalysisDate: '2026-02-11',
    riskScore: 42,
    riskLevel: 'medium',
  },
  {
    id: 'c-008',
    name: '英国金融子会社',
    nameEn: 'UK Financial Services Ltd.',
    country: 'イギリス',
    region: 'EMEA',
    ownershipPct: 100,
    consolidationType: 'full',
    industry: '金融業',
    fiscalYearEnd: '3月',
    lastAnalysisDate: '2026-02-13',
    riskScore: 61,
    riskLevel: 'high',
  },
  {
    id: 'c-009',
    name: 'オーストラリア販売子会社',
    nameEn: 'Australia Sales Pty Ltd.',
    country: 'オーストラリア',
    region: 'APAC',
    ownershipPct: 100,
    consolidationType: 'full',
    industry: '卸売業',
    fiscalYearEnd: '6月',
    lastAnalysisDate: '2026-02-09',
    riskScore: 18,
    riskLevel: 'low',
  },
  {
    id: 'c-010',
    name: 'シンガポール持株子会社',
    nameEn: 'Singapore Holdings Pte. Ltd.',
    country: 'シンガポール',
    region: 'APAC',
    ownershipPct: 100,
    consolidationType: 'full',
    industry: '持株会社',
    fiscalYearEnd: '3月',
    lastAnalysisDate: '2026-02-07',
    riskScore: 90,
    riskLevel: 'critical',
  },
]

/** リスクレベルの表示設定 */
const riskLevelConfig: Record<
  RiskLevel,
  { icon: typeof AlertTriangle; colorClass: string; bgClass: string; label: string }
> = {
  critical: {
    icon: AlertTriangle,
    colorClass: 'text-risk-critical',
    bgClass: 'bg-risk-critical/10',
    label: 'クリティカル',
  },
  high: {
    icon: AlertCircle,
    colorClass: 'text-risk-high',
    bgClass: 'bg-risk-high/10',
    label: '高',
  },
  medium: {
    icon: Info,
    colorClass: 'text-risk-medium',
    bgClass: 'bg-risk-medium/10',
    label: '中',
  },
  low: {
    icon: CheckCircle,
    colorClass: 'text-risk-low',
    bgClass: 'bg-risk-low/10',
    label: '低',
  },
}

type SortField = 'name' | 'riskScore' | 'country' | 'lastAnalysisDate'
type SortDirection = 'asc' | 'desc'

/**
 * 企業テーブル
 * 連結子会社の一覧をリスクスコア付きで表示
 */
export function CompanyTable() {
  const [sortField, setSortField] = useState<SortField>('riskScore')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterRiskLevel, setFilterRiskLevel] = useState<RiskLevel | 'all'>('all')

  /** ソート切替 */
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  /** フィルタ・ソート適用 */
  const filteredCompanies = mockCompanies
    .filter((c) => filterRiskLevel === 'all' || c.riskLevel === filterRiskLevel)
    .sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1
      switch (sortField) {
        case 'name':
          return dir * a.name.localeCompare(b.name, 'ja')
        case 'riskScore':
          return dir * ((a.riskScore ?? 0) - (b.riskScore ?? 0))
        case 'country':
          return dir * a.country.localeCompare(b.country, 'ja')
        case 'lastAnalysisDate':
          return (
            dir *
            ((a.lastAnalysisDate ?? '').localeCompare(b.lastAnalysisDate ?? ''))
          )
        default:
          return 0
      }
    })

  const SortButton = ({
    field,
    children,
  }: {
    field: SortField
    children: React.ReactNode
  }) => (
    <button
      onClick={() => handleSort(field)}
      className="flex items-center gap-1 text-xs font-medium uppercase text-muted-foreground hover:text-foreground transition-colors"
    >
      {children}
      <ArrowUpDown className="h-3 w-3" />
    </button>
  )

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* フィルターバー */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-4">
        <span className="text-sm text-muted-foreground">リスクレベル:</span>
        {(['all', 'critical', 'high', 'medium', 'low'] as const).map((level) => (
          <button
            key={level}
            onClick={() => setFilterRiskLevel(level)}
            className={`
              rounded-full px-3 py-1 text-xs font-medium transition-colors
              ${
                filterRiskLevel === level
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-accent hover:text-accent-foreground'
              }
            `}
          >
            {level === 'all'
              ? `すべて (${mockCompanies.length})`
              : `${riskLevelConfig[level].label} (${mockCompanies.filter((c) => c.riskLevel === level).length})`}
          </button>
        ))}
      </div>

      {/* テーブル */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="px-6 py-3 text-left">
                <SortButton field="name">企業名</SortButton>
              </th>
              <th className="px-6 py-3 text-left">
                <SortButton field="country">国</SortButton>
              </th>
              <th className="px-6 py-3 text-left">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  地域
                </span>
              </th>
              <th className="px-6 py-3 text-left">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  出資比率
                </span>
              </th>
              <th className="px-6 py-3 text-left">
                <SortButton field="riskScore">リスクスコア</SortButton>
              </th>
              <th className="px-6 py-3 text-left">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  リスクレベル
                </span>
              </th>
              <th className="px-6 py-3 text-left">
                <SortButton field="lastAnalysisDate">最終分析日</SortButton>
              </th>
              <th className="px-6 py-3 text-right">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  操作
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredCompanies.map((company) => {
              const risk = company.riskLevel
                ? riskLevelConfig[company.riskLevel]
                : null
              const RiskIcon = risk?.icon

              return (
                <tr
                  key={company.id}
                  className="border-b border-border last:border-0 hover:bg-accent/30 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div>
                      <p className="text-sm font-medium text-card-foreground">
                        {company.name}
                      </p>
                      {company.nameEn && (
                        <p className="text-xs text-muted-foreground">
                          {company.nameEn}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-card-foreground">
                    {company.country}
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {company.region}
                  </td>
                  <td className="px-6 py-4 text-sm text-card-foreground">
                    {company.ownershipPct}%
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-16 rounded-full bg-muted">
                        <div
                          className="h-2 rounded-full transition-all"
                          style={{
                            width: `${company.riskScore ?? 0}%`,
                            backgroundColor:
                              company.riskLevel === 'critical'
                                ? '#dc2626'
                                : company.riskLevel === 'high'
                                  ? '#f97316'
                                  : company.riskLevel === 'medium'
                                    ? '#eab308'
                                    : '#22c55e',
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium text-card-foreground">
                        {company.riskScore ?? '-'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {risk && RiskIcon && (
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${risk.bgClass} ${risk.colorClass}`}
                      >
                        <RiskIcon className="h-3 w-3" />
                        {risk.label}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {company.lastAnalysisDate ?? '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                      title="詳細を表示"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      詳細
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* テーブルフッター */}
      <div className="flex items-center justify-between border-t border-border px-6 py-3">
        <p className="text-xs text-muted-foreground">
          {filteredCompanies.length}社を表示中 (全{mockCompanies.length}社)
        </p>
      </div>
    </div>
  )
}
