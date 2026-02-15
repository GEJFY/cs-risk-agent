'use client'

import { useState, useEffect } from 'react'
import {
  ArrowUpDown,
  ExternalLink,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  Loader2,
} from 'lucide-react'
import type { RiskLevel } from '@/types'
import { fetchAPI } from '@/lib/api-client'
import Link from 'next/link'

/** バックエンドエンティティ型 */
interface BackendEntity {
  id: string
  name: string
  name_en?: string
  country: string
  segment?: string
  region?: string
  ownership_pct?: number
  ownership_ratio?: number
  total_score?: number
  risk_level?: string
  risk_factors?: string[]
}

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

type SortField = 'name' | 'riskScore' | 'country'
type SortDirection = 'asc' | 'desc'

/**
 * 企業テーブル
 * 連結子会社の一覧をリスクスコア付きで表示
 */
export function CompanyTable() {
  const [companies, setCompanies] = useState<BackendEntity[]>([])
  const [loading, setLoading] = useState(true)
  const [sortField, setSortField] = useState<SortField>('riskScore')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterRiskLevel, setFilterRiskLevel] = useState<RiskLevel | 'all'>('all')

  useEffect(() => {
    fetchAPI<{ items: BackendEntity[]; total: number; page: number; per_page: number; pages: number }>(
      '/api/v1/companies/?per_page=50'
    )
      .then((data) => setCompanies(data.items))
      .catch((e) => console.error('Failed to fetch companies:', e))
      .finally(() => setLoading(false))
  }, [])

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
  const filteredCompanies = companies
    .filter((c) => filterRiskLevel === 'all' || c.risk_level === filterRiskLevel)
    .sort((a, b) => {
      const dir = sortDirection === 'asc' ? 1 : -1
      switch (sortField) {
        case 'name':
          return dir * a.name.localeCompare(b.name, 'ja')
        case 'riskScore':
          return dir * ((a.total_score ?? 0) - (b.total_score ?? 0))
        case 'country':
          return dir * (a.country ?? '').localeCompare(b.country ?? '', 'ja')
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

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

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
              ? `すべて (${companies.length})`
              : `${riskLevelConfig[level].label} (${companies.filter((c) => c.risk_level === level).length})`}
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
                  セグメント
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
              <th className="px-6 py-3 text-right">
                <span className="text-xs font-medium uppercase text-muted-foreground">
                  操作
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredCompanies.map((company) => {
              const riskLevel = company.risk_level as RiskLevel | undefined
              const risk = riskLevel ? riskLevelConfig[riskLevel] : null
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
                      {company.name_en && (
                        <p className="text-xs text-muted-foreground">
                          {company.name_en}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-card-foreground">
                    {company.country}
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">
                    {company.segment ?? '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-card-foreground">
                    {company.ownership_ratio ? `${company.ownership_ratio}%` : company.ownership_pct ? `${company.ownership_pct}%` : '100%'}
                  </td>
                  <td className="px-6 py-4">
                    {company.total_score != null ? (
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 rounded-full bg-muted">
                          <div
                            className="h-2 rounded-full transition-all"
                            style={{
                              width: `${company.total_score}%`,
                              backgroundColor:
                                riskLevel === 'critical'
                                  ? '#dc2626'
                                  : riskLevel === 'high'
                                    ? '#f97316'
                                    : riskLevel === 'medium'
                                      ? '#eab308'
                                      : '#22c55e',
                            }}
                          />
                        </div>
                        <span className="text-sm font-medium text-card-foreground">
                          {company.total_score}
                        </span>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
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
                  <td className="px-6 py-4 text-right">
                    <Link
                      href={`/subsidiaries/${company.id}`}
                      className="inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      詳細
                    </Link>
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
          {filteredCompanies.length}社を表示中 (全{companies.length}社)
        </p>
      </div>
    </div>
  )
}
