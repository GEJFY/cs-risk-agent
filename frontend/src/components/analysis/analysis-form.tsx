'use client'

import { useState } from 'react'
import {
  PlayCircle,
  Loader2,
  CheckCircle,
  Building2,
  Brain,
} from 'lucide-react'
import { useAppStore } from '@/stores/app-store'

/** 分析対象の企業リスト (デモ用) */
const mockCompanyOptions = [
  { id: 'c-001', name: '東南アジア製造子会社' },
  { id: 'c-002', name: '欧州販売子会社' },
  { id: 'c-003', name: '北米IT子会社' },
  { id: 'c-004', name: '中国物流子会社' },
  { id: 'c-005', name: 'インド開発子会社' },
  { id: 'c-006', name: 'ブラジル資源子会社' },
  { id: 'c-007', name: '韓国電子部品子会社' },
  { id: 'c-008', name: '英国金融子会社' },
  { id: 'c-009', name: 'オーストラリア販売子会社' },
  { id: 'c-010', name: 'シンガポール持株子会社' },
]

/** 分析タイプ */
const analysisTypes = [
  {
    id: 'comprehensive',
    name: '総合リスク分析',
    description: '財務・運営・コンプライアンス・戦略の全カテゴリを分析',
    estimatedTime: '約3-5分',
  },
  {
    id: 'financial',
    name: '財務リスク分析',
    description: '財務諸表・連結パッケージに特化した分析',
    estimatedTime: '約1-2分',
  },
  {
    id: 'compliance',
    name: 'コンプライアンス分析',
    description: '法規制・内部規程の遵守状況を分析',
    estimatedTime: '約2-3分',
  },
  {
    id: 'operational',
    name: 'オペレーショナルリスク分析',
    description: '業務プロセス・IT・人的リスクを分析',
    estimatedTime: '約2-3分',
  },
]

/**
 * 分析実行フォーム
 * 対象企業と分析タイプを選択して分析を実行
 */
export function AnalysisForm() {
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([])
  const [selectedAnalysisType, setSelectedAnalysisType] = useState<string>('comprehensive')
  const [isRunning, setIsRunning] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const { setAnalysisRunning } = useAppStore()

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
    if (selectedCompanies.length === mockCompanyOptions.length) {
      setSelectedCompanies([])
    } else {
      setSelectedCompanies(mockCompanyOptions.map((c) => c.id))
    }
  }

  /** 分析実行 (デモ) */
  const handleRunAnalysis = async () => {
    if (selectedCompanies.length === 0) return

    setIsRunning(true)
    setIsCompleted(false)
    setAnalysisRunning(true)

    // デモ用: 3秒後に完了
    await new Promise((resolve) => setTimeout(resolve, 3000))

    setIsRunning(false)
    setIsCompleted(true)
    setAnalysisRunning(false)
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
            {selectedCompanies.length === mockCompanyOptions.length
              ? 'すべて解除'
              : 'すべて選択'}
          </button>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {mockCompanyOptions.map((company) => {
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
              分析が完了しました ({selectedCompanies.length}社)
            </span>
          </div>
        )}
      </div>

      {/* 実行中のプログレス */}
      {isRunning && (
        <div className="rounded-xl border border-border bg-card p-6 animate-fade-in">
          <h4 className="text-sm font-semibold text-card-foreground">
            分析進行状況
          </h4>
          <div className="mt-4 space-y-3">
            {selectedCompanies.slice(0, 3).map((companyId, index) => {
              const company = mockCompanyOptions.find((c) => c.id === companyId)
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
                        ? 'AI分析待ち...'
                        : '待機中...'}
                  </span>
                </div>
              )
            })}
            {selectedCompanies.length > 3 && (
              <p className="text-xs text-muted-foreground">
                他 {selectedCompanies.length - 3}社 待機中...
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
