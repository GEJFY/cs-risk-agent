'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  PlayCircle,
  Loader2,
  CheckCircle,
  Building2,
  Brain,
  AlertTriangle,
  BarChart3,
} from 'lucide-react'
import { useAppStore } from '@/stores/app-store'
import { fetchAPI } from '@/lib/api-client'

/** バックエンドエンティティ型 */
interface CompanyOption {
  id: string
  name: string
}

/** 分析タイプとエンジンのマッピング */
const analysisTypes = [
  {
    id: 'comprehensive',
    name: '総合リスク分析',
    description: '裁量的発生高・不正予測・ルールエンジン・ベンフォードの全エンジンで分析',
    engines: ['da', 'fraud', 'rule', 'benford'],
  },
  {
    id: 'financial',
    name: '財務リスク分析',
    description: '財務諸表・仕訳データに特化した分析',
    engines: ['da', 'fraud', 'rule'],
  },
  {
    id: 'compliance',
    name: 'コンプライアンス分析',
    description: 'ルールエンジンによる内部規程遵守状況の分析',
    engines: ['rule'],
  },
  {
    id: 'benford',
    name: 'ベンフォード分析',
    description: '数値分布の自然法則との逸脱を検証',
    engines: ['benford'],
  },
]

/** タスクステータス */
interface TaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  completed_steps: number
  total_steps: number
  error: string | null
  result_count: number
}

/** 分析結果 */
interface AnalysisResultItem {
  id: string
  company_id: string
  company_name: string
  total_score: number
  risk_level: string
  da_score: number
  fraud_score: number
  rule_score: number
  benford_score: number
  risk_factors: string[]
  summary?: string
}

/**
 * 分析実行フォーム (非同期パイプライン対応)
 * 対象企業と分析タイプを選択し、バックグラウンドで分析を実行
 */
export function AnalysisForm() {
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [selectedAnalysisType, setSelectedAnalysisType] = useState<string>('comprehensive')
  const [isRunning, setIsRunning] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<AnalysisResultItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const { setAnalysisRunning } = useAppStore()
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

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

  /** ポーリング停止 */
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  /** クリーンアップ */
  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  /** タスクステータスのポーリング */
  const startPolling = useCallback(
    (tid: string) => {
      stopPolling()
      pollingRef.current = setInterval(async () => {
        try {
          const status = await fetchAPI<TaskStatus>(
            `/api/v1/analysis/tasks/${tid}`
          )
          setProgress(status.progress)

          if (status.status === 'completed') {
            stopPolling()
            // 結果取得
            const resultData = await fetchAPI<{
              results: AnalysisResultItem[]
            }>(`/api/v1/analysis/tasks/${tid}/results`)
            setResults(resultData.results)
            setIsCompleted(true)
            setIsRunning(false)
            setAnalysisRunning(false)
          } else if (status.status === 'failed') {
            stopPolling()
            setError(status.error || '分析に失敗しました')
            setIsRunning(false)
            setAnalysisRunning(false)
          }
        } catch {
          // ポーリングエラーは無視（次回リトライ）
        }
      }, 2000)
    },
    [stopPolling, setAnalysisRunning]
  )

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

  /** 分析実行 (非同期) */
  const handleRunAnalysis = async () => {
    if (selectedCompanies.length === 0) return

    setIsRunning(true)
    setIsCompleted(false)
    setResults([])
    setError(null)
    setProgress(0)
    setTaskId(null)
    setAnalysisRunning(true)

    const selectedType = analysisTypes.find((t) => t.id === selectedAnalysisType)

    try {
      const data = await fetchAPI<{ task_id: string; status: string }>(
        '/api/v1/analysis/run-async',
        {
          method: 'POST',
          body: JSON.stringify({
            company_ids: selectedCompanies,
            fiscal_year: 2025,
            fiscal_quarter: 4,
            analysis_types: selectedType?.engines || ['da', 'fraud', 'rule', 'benford'],
          }),
        }
      )
      setTaskId(data.task_id)
      startPolling(data.task_id)
    } catch (e) {
      console.error('Analysis failed:', e)
      setError('分析の開始に失敗しました')
      setIsRunning(false)
      setAnalysisRunning(false)
    }
  }

  /** リスクレベルに応じた色 */
  const riskColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'text-risk-critical'
      case 'high':
        return 'text-risk-high'
      case 'medium':
        return 'text-risk-medium'
      default:
        return 'text-risk-low'
    }
  }

  const riskBgColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/20'
      case 'high':
        return 'bg-orange-500/10 border-orange-500/20'
      case 'medium':
        return 'bg-yellow-500/10 border-yellow-500/20'
      default:
        return 'bg-green-500/10 border-green-500/20'
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
                エンジン: {type.engines.join(', ')}
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

      {/* エラー表示 */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-500/20 bg-red-500/10 p-4">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          <span className="text-sm text-red-500">{error}</span>
        </div>
      )}

      {/* 実行中のプログレス */}
      {isRunning && (
        <div className="rounded-xl border border-border bg-card p-6 animate-fade-in">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-card-foreground">
              分析進行状況
            </h4>
            {taskId && (
              <span className="text-[10px] text-muted-foreground font-mono">
                Task: {taskId.slice(0, 8)}...
              </span>
            )}
          </div>

          {/* プログレスバー */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground">進捗</span>
              <span className="text-xs font-medium text-primary">{progress}%</span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted">
              <div
                className="h-2 rounded-full bg-primary transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <div className="space-y-2">
            {selectedCompanies.slice(0, 5).map((companyId) => {
              const company = companyOptions.find((c) => c.id === companyId)
              return (
                <div key={companyId} className="flex items-center gap-3">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                  <span className="text-sm text-card-foreground">
                    {company?.name}
                  </span>
                </div>
              )
            })}
            {selectedCompanies.length > 5 && (
              <p className="text-xs text-muted-foreground">
                他 {selectedCompanies.length - 5}社 処理中...
              </p>
            )}
          </div>
        </div>
      )}

      {/* 分析結果 */}
      {isCompleted && results.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6 animate-fade-in">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-5 w-5 text-primary" />
            <h4 className="text-sm font-semibold text-card-foreground">
              分析結果 ({results.length}社)
            </h4>
          </div>
          <div className="space-y-3">
            {results.map((r) => (
              <div
                key={r.id}
                className={`rounded-lg border p-4 ${riskBgColor(r.risk_level)}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-medium text-card-foreground">
                    {r.company_name}
                  </p>
                  <div className="text-right">
                    <p className={`text-lg font-bold ${riskColor(r.risk_level)}`}>
                      {r.total_score}
                    </p>
                    <p className={`text-xs font-medium ${riskColor(r.risk_level)}`}>
                      {r.risk_level.toUpperCase()}
                    </p>
                  </div>
                </div>

                {/* エンジン別スコア */}
                <div className="grid grid-cols-4 gap-2 mb-2">
                  {[
                    { label: 'ルール', score: r.rule_score },
                    { label: '不正予測', score: r.fraud_score },
                    { label: 'DA', score: r.da_score },
                    { label: 'ベンフォード', score: r.benford_score },
                  ].map((eng) => (
                    <div key={eng.label} className="text-center">
                      <p className="text-[10px] text-muted-foreground">
                        {eng.label}
                      </p>
                      <p className="text-xs font-semibold text-card-foreground">
                        {eng.score}
                      </p>
                    </div>
                  ))}
                </div>

                {/* リスクファクター */}
                {r.risk_factors.length > 0 && (
                  <div className="mt-2 border-t border-border/50 pt-2">
                    <p className="text-[10px] font-medium text-muted-foreground mb-1">
                      検出されたリスクファクター:
                    </p>
                    {r.risk_factors.slice(0, 3).map((f, i) => (
                      <p key={i} className="text-xs text-muted-foreground">
                        {f}
                      </p>
                    ))}
                    {r.risk_factors.length > 3 && (
                      <p className="text-[10px] text-muted-foreground">
                        他 {r.risk_factors.length - 3}件
                      </p>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
