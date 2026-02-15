'use client'

import { useState, useEffect } from 'react'
import {
  PlayCircle,
  Loader2,
  CheckCircle,
  Building2,
  Brain,
} from 'lucide-react'
import { useAppStore } from '@/stores/app-store'
import { fetchAPI } from '@/lib/api-client'

/** バックエンドエンティティ型 */
interface CompanyOption {
  id: string
  name: string
}

/** 分析タイプ */
const analysisTypes = [
  {
    id: 'comprehensive',
    name: '総合リスク分析',
    description: '裁量的発生高・不正予測・ルールエンジン・ベンフォードの全エンジンで分析',
    estimatedTime: '約3-5分',
  },
  {
    id: 'financial',
    name: '財務リスク分析',
    description: '財務諸表・仕訳データに特化した分析',
    estimatedTime: '約1-2分',
  },
  {
    id: 'compliance',
    name: 'コンプライアンス分析',
    description: 'ルールエンジンによる内部規程遵守状況の分析',
    estimatedTime: '約2-3分',
  },
  {
    id: 'benford',
    name: 'ベンフォード分析',
    description: '数値分布の自然法則との逸脱を検証',
    estimatedTime: '約1-2分',
  },
]

/** 分析結果 */
interface AnalysisResultItem {
  id: string
  company_id: string
  company_name: string
  total_score: number
  risk_level: string
  risk_factors: string[]
}

/**
 * 分析実行フォーム
 * 対象企業と分析タイプを選択して分析を実行
 */
export function AnalysisForm() {
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [selectedAnalysisType, setSelectedAnalysisType] = useState<string>('comprehensive')
  const [isRunning, setIsRunning] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [results, setResults] = useState<AnalysisResultItem[]>([])
  const { setAnalysisRunning } = useAppStore()

  /** APIから企業一覧を取得 */
  useEffect(() => {
    fetchAPI<{ items: Array<{ id: string; name: string }>; total: number }>(
      '/api/v1/companies/?per_page=50'
    )
      .then((data) => {
        setCompanyOptions(data.items.map((c) => ({ id: c.id, name: c.name })))
      })
      .catch((e) => console.error('Failed to fetch companies:', e))
  }, [])

  /** 企業選択のトグル */
  const toggleCompany = (companyId: string) => {
    setSelectedCompanies((prev) =>
      prev.includes(companyId)
        ? prev.filter((id) => id !== companyId)
        : [...prev, companyId]
    )
  }

  /** 全選択/全解除 */
  const toggleAll = () => {
    if (selectedCompanies.length === companyOptions.length) {
      setSelectedCompanies([])
    } else {
      setSelectedCompanies(companyOptions.map((c) => c.id))
    }
  }

  /** 分析実行 */
  const handleRunAnalysis = async () => {
    if (selectedCompanies.length === 0) return

    setIsRunning(true)
    setIsCompleted(false)
    setResults([])
    setAnalysisRunning(true)

    try {
      const data = await fetchAPI<{ status: string; results: AnalysisResultItem[] }>(
        '/api/v1/analysis/run',
        {
          method: 'POST',
          body: JSON.stringify({
            company_ids: selectedCompanies,
            fiscal_year: 2025,
            fiscal_quarter: 4,
            analysis_types: [selectedAnalysisType],
          }),
        }
      )
      setResults(data.results)
      setIsCompleted(true)
    } catch (e) {
      console.error('Analysis failed:', e)
    } finally {
      setIsRunning(false)
      setAnalysisRunning(false)
    }
  }

  /** リスクレベルに応じた色 */
  const riskColor = (level: string) => {
    switch (level) {
      case 'critical': return 'text-risk-critical'
      case 'high': return 'text-risk-high'
      case 'medium': return 'text-risk-medium'
      default: return 'text-risk-low'
    }
  }

  return (
    <div className="space-y-6">
      {/* 企業選択セクション */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Building2 className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            対象企業の選択
          </h3>
        </div>

        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            分析対象の連結子会社を選択してください
          </p>
          <button
            onClick={toggleAll}
            className="text-xs font-medium text-primary hover:underline"
          >
            {selectedCompanies.length === companyOptions.length
              ? 'すべて解除'
              : 'すべて選択'}
          </button>
        </div>

        {companyOptions.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {companyOptions.map((company) => {
              const isSelected = selectedCompanies.includes(company.id)
              return (
                <label
                  key={company.id}
                  className={`
                    flex cursor-pointer items-center gap-3 rounded-lg border p-3
                    transition-colors
                    ${
                      isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-accent/50'
                    }
                  `}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleCompany(company.id)}
                    className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  />
                  <span className="text-sm text-card-foreground">
                    {company.name}
                  </span>
                </label>
              )
            })}
          </div>
        )}

        <p className="mt-3 text-xs text-muted-foreground">
          {selectedCompanies.length}社を選択中
        </p>
      </div>

      {/* 分析タイプ選択セクション */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            分析タイプの選択
          </h3>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {analysisTypes.map((type) => (
            <label
              key={type.id}
              className={`
                flex cursor-pointer flex-col rounded-lg border p-4
                transition-colors
                ${
                  selectedAnalysisType === type.id
                    ? 'border-primary bg-primary/5'
                    : 'border-border hover:bg-accent/50'
                }
              `}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="analysisType"
                  value={type.id}
                  checked={selectedAnalysisType === type.id}
                  onChange={() => setSelectedAnalysisType(type.id)}
                  className="h-4 w-4 border-border text-primary focus:ring-primary"
                />
                <span className="text-sm font-medium text-card-foreground">
                  {type.name}
                </span>
              </div>
              <p className="mt-1.5 pl-6 text-xs text-muted-foreground">
                {type.description}
              </p>
              <p className="mt-1 pl-6 text-[10px] text-muted-foreground">
                所要時間: {type.estimatedTime}
              </p>
            </label>
          ))}
        </div>
      </div>

      {/* 実行ボタン */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleRunAnalysis}
          disabled={selectedCompanies.length === 0 || isRunning}
          className={`
            inline-flex items-center gap-2 rounded-lg px-6 py-3
            text-sm font-medium transition-colors
            ${
              selectedCompanies.length === 0 || isRunning
                ? 'cursor-not-allowed bg-muted text-muted-foreground'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            }
          `}
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              分析実行中...
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4" />
              分析を実行
            </>
          )}
        </button>

        {isCompleted && (
          <div className="flex items-center gap-2 text-risk-low">
            <CheckCircle className="h-5 w-5" />
            <span className="text-sm font-medium">
              分析が完了しました ({results.length}社)
            </span>
          </div>
        )}
      </div>

      {/* 分析結果 */}
      {isCompleted && results.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6 animate-fade-in">
          <h4 className="text-sm font-semibold text-card-foreground mb-4">
            分析結果
          </h4>
          <div className="space-y-3">
            {results.map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-border p-3">
                <div>
                  <p className="text-sm font-medium text-card-foreground">{r.company_name}</p>
                  {r.risk_factors.length > 0 && (
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-1">
                      {r.risk_factors[0]}
                    </p>
                  )}
                </div>
                <div className="text-right">
                  <p className={`text-lg font-bold ${riskColor(r.risk_level)}`}>
                    {r.total_score}
                  </p>
                  <p className={`text-xs ${riskColor(r.risk_level)}`}>
                    {r.risk_level.toUpperCase()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 実行中のプログレス */}
      {isRunning && (
        <div className="rounded-xl border border-border bg-card p-6 animate-fade-in">
          <h4 className="text-sm font-semibold text-card-foreground">
            分析進行状況
          </h4>
          <div className="mt-4 space-y-3">
            {selectedCompanies.slice(0, 5).map((companyId, index) => {
              const company = companyOptions.find((c) => c.id === companyId)
              return (
                <div key={companyId} className="flex items-center gap-3">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm text-card-foreground">
                    {company?.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {index === 0
                      ? 'データ収集中...'
                      : index === 1
                        ? 'AI分析中...'
                        : '待機中...'}
                  </span>
                </div>
              )
            })}
            {selectedCompanies.length > 5 && (
              <p className="text-xs text-muted-foreground">
                他 {selectedCompanies.length - 5}社 待機中...
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
