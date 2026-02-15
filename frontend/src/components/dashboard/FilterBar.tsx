'use client'

import { useFilterStore } from '@/stores/filter-store'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RotateCcw } from 'lucide-react'

/** 業種選択肢 */
const INDUSTRY_OPTIONS = [
  { value: '', label: '全業種' },
  { value: '3250', label: '電気機器' },
  { value: '3300', label: '機械' },
  { value: '3350', label: '精密機器' },
  { value: '3400', label: '輸送用機器' },
  { value: '3050', label: '医薬品' },
  { value: '4050', label: '情報・通信業' },
  { value: '5050', label: '卸売業' },
  { value: '5100', label: '小売業' },
  { value: '6050', label: '銀行業' },
  { value: '6100', label: '証券・商品先物取引業' },
]

/** リスクレベル選択肢 */
const RISK_LEVEL_OPTIONS = [
  { value: '', label: '全リスクレベル' },
  { value: 'critical', label: '重大 (Critical)' },
  { value: 'high', label: '高 (High)' },
  { value: 'medium', label: '中 (Medium)' },
  { value: 'low', label: '低 (Low)' },
]

/** 会計年度選択肢 */
const FISCAL_YEAR_OPTIONS = [2024, 2023, 2022, 2021, 2020]

/** 四半期選択肢 */
const QUARTER_OPTIONS = [
  { value: 4, label: '通期 (Q4)' },
  { value: 3, label: 'Q3' },
  { value: 2, label: 'Q2' },
  { value: 1, label: 'Q1' },
]

interface FilterBarProps {
  className?: string
}

/**
 * フィルターバーコンポーネント
 * ダッシュボードの絞り込み条件を管理するバー
 */
export function FilterBar({ className }: FilterBarProps) {
  const {
    fiscalYear,
    fiscalQuarter,
    industryCode,
    riskLevel,
    setFiscalYear,
    setFiscalQuarter,
    setIndustryCode,
    setRiskLevel,
    resetFilters,
  } = useFilterStore()

  return (
    <Card className={className}>
      <CardContent className="py-3 px-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* 会計年度 */}
          <div className="flex items-center gap-1.5">
            <label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
              年度
            </label>
            <select
              value={fiscalYear}
              onChange={(e) => setFiscalYear(Number(e.target.value))}
              className="h-8 px-2 rounded-md border border-input bg-background text-sm
                focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {FISCAL_YEAR_OPTIONS.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>

          {/* 四半期 */}
          <div className="flex items-center gap-1.5">
            <label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
              期間
            </label>
            <select
              value={fiscalQuarter}
              onChange={(e) => setFiscalQuarter(Number(e.target.value))}
              className="h-8 px-2 rounded-md border border-input bg-background text-sm
                focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {QUARTER_OPTIONS.map((q) => (
                <option key={q.value} value={q.value}>
                  {q.label}
                </option>
              ))}
            </select>
          </div>

          {/* 業種 */}
          <div className="flex items-center gap-1.5">
            <label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
              業種
            </label>
            <select
              value={industryCode || ''}
              onChange={(e) =>
                setIndustryCode(e.target.value || null)
              }
              className="h-8 px-2 rounded-md border border-input bg-background text-sm
                focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {INDUSTRY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* リスクレベル */}
          <div className="flex items-center gap-1.5">
            <label className="text-xs font-medium text-muted-foreground whitespace-nowrap">
              リスク
            </label>
            <select
              value={riskLevel || ''}
              onChange={(e) =>
                setRiskLevel(e.target.value || null)
              }
              className="h-8 px-2 rounded-md border border-input bg-background text-sm
                focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {RISK_LEVEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* リセットボタン */}
          <Button
            variant="ghost"
            size="sm"
            onClick={resetFilters}
            className="ml-auto text-xs text-muted-foreground"
          >
            <RotateCcw className="w-3 h-3 mr-1" />
            リセット
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
