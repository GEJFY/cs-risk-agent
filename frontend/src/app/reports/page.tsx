'use client'

import { useState, useEffect } from 'react'
import { FileDown, FileText, Presentation, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { useAppStore } from '@/stores/app-store'
import { fetchAPI } from '@/lib/api-client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005'

/** 企業情報 (リスクスコア付き) */
interface Entity {
  id: string
  name: string
  risk_level?: string
  total_score?: number
}

/** レポート生成結果 */
interface ReportResult {
  report_id: string
  status: string
  download_url: string | null
}

/**
 * レポートページ
 * PDF/PPTX 形式のリスク分析レポートを生成・ダウンロード
 */
export default function ReportsPage() {
  const { sidebarOpen } = useAppStore()
  const [entities, setEntities] = useState<Entity[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [format, setFormat] = useState<'pdf' | 'pptx'>('pdf')
  const [language, setLanguage] = useState<'ja' | 'en'>('ja')
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<ReportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAPI<{ items: Entity[]; total: number }>('/api/v1/risk-scores/')
      .then((data) => setEntities(data.items))
      .catch((e) => console.error('Failed to fetch entities:', e))
  }, [])

  const handleSelectAll = () => {
    if (selectedIds.length === entities.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(entities.map((e) => e.id))
    }
  }

  const toggleEntity = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setResult(null)
    setError(null)

    try {
      const res = await fetchAPI<ReportResult>('/api/v1/reports/generate', {
        method: 'POST',
        body: JSON.stringify({
          company_ids: selectedIds.length > 0 ? selectedIds : [],
          fiscal_year: 2025,
          format,
          sections: ['summary', 'risk_scores', 'alerts', 'recommendations'],
          language,
        }),
      })
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'レポート生成に失敗しました')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = () => {
    if (!result?.download_url) return
    window.open(`${API_BASE}${result.download_url}`, '_blank')
  }

  return (
    <div
      className={`
        space-y-6 transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* ヘッダー */}
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2.5">
          <FileDown className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">レポート生成</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            PDF/PPTX 形式のリスク分析レポート
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 設定パネル */}
        <div className="lg:col-span-2 space-y-4">
          {/* フォーマット選択 */}
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="text-base font-semibold text-card-foreground mb-4">
              出力設定
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setFormat('pdf')}
                className={`
                  flex items-center gap-3 rounded-lg border p-4 transition-all
                  ${format === 'pdf'
                    ? 'border-primary bg-primary/5 ring-1 ring-primary'
                    : 'border-border hover:bg-accent/30'
                  }
                `}
              >
                <FileText className={`h-8 w-8 ${format === 'pdf' ? 'text-primary' : 'text-muted-foreground'}`} />
                <div className="text-left">
                  <p className="text-sm font-medium text-card-foreground">PDF</p>
                  <p className="text-xs text-muted-foreground">監査委員会向け報告書</p>
                </div>
              </button>
              <button
                onClick={() => setFormat('pptx')}
                className={`
                  flex items-center gap-3 rounded-lg border p-4 transition-all
                  ${format === 'pptx'
                    ? 'border-primary bg-primary/5 ring-1 ring-primary'
                    : 'border-border hover:bg-accent/30'
                  }
                `}
              >
                <Presentation className={`h-8 w-8 ${format === 'pptx' ? 'text-primary' : 'text-muted-foreground'}`} />
                <div className="text-left">
                  <p className="text-sm font-medium text-card-foreground">PPTX</p>
                  <p className="text-xs text-muted-foreground">経営会議用プレゼン資料</p>
                </div>
              </button>
            </div>

            <div className="mt-4 flex items-center gap-4">
              <span className="text-sm text-muted-foreground">言語:</span>
              <button
                onClick={() => setLanguage('ja')}
                className={`rounded-md px-3 py-1 text-sm ${language === 'ja' ? 'bg-primary text-primary-foreground' : 'bg-accent text-accent-foreground'}`}
              >
                日本語
              </button>
              <button
                onClick={() => setLanguage('en')}
                className={`rounded-md px-3 py-1 text-sm ${language === 'en' ? 'bg-primary text-primary-foreground' : 'bg-accent text-accent-foreground'}`}
              >
                English
              </button>
            </div>
          </div>

          {/* 対象企業選択 */}
          <div className="rounded-xl border border-border bg-card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-card-foreground">
                対象企業
              </h3>
              <button
                onClick={handleSelectAll}
                className="text-xs text-primary hover:underline"
              >
                {selectedIds.length === entities.length ? '全解除' : '全選択'}
              </button>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              未選択の場合は全社が対象になります
            </p>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {entities.map((entity) => (
                <label
                  key={entity.id}
                  className="flex items-center gap-3 rounded-lg border border-border p-3 cursor-pointer hover:bg-accent/30 transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(entity.id)}
                    onChange={() => toggleEntity(entity.id)}
                    className="rounded border-border"
                  />
                  <span className="text-sm text-card-foreground flex-1">
                    {entity.name}
                  </span>
                  {entity.risk_level && (
                    <span
                      className={`
                        rounded-full px-2 py-0.5 text-[10px] font-medium
                        ${entity.risk_level === 'critical' ? 'bg-risk-critical/10 text-risk-critical' :
                          entity.risk_level === 'high' ? 'bg-risk-high/10 text-risk-high' :
                          entity.risk_level === 'medium' ? 'bg-risk-medium/10 text-risk-medium' :
                          'bg-risk-low/10 text-risk-low'}
                      `}
                    >
                      {entity.risk_level}
                    </span>
                  )}
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* 生成・ダウンロードパネル */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="text-base font-semibold text-card-foreground mb-4">
              レポート生成
            </h3>

            <div className="space-y-3 text-sm text-muted-foreground mb-6">
              <p>形式: <span className="font-medium text-card-foreground">{format.toUpperCase()}</span></p>
              <p>言語: <span className="font-medium text-card-foreground">{language === 'ja' ? '日本語' : 'English'}</span></p>
              <p>対象: <span className="font-medium text-card-foreground">{selectedIds.length > 0 ? `${selectedIds.length}社` : '全社'}</span></p>
              <p>年度: <span className="font-medium text-card-foreground">2025</span></p>
            </div>

            <button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full rounded-lg bg-primary px-4 py-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {generating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <FileDown className="h-4 w-4" />
                  レポート生成
                </>
              )}
            </button>

            {/* 結果表示 */}
            {result && result.status === 'completed' && (
              <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium text-green-700 dark:text-green-400">
                    生成完了
                  </span>
                </div>
                <button
                  onClick={handleDownload}
                  className="w-full mt-2 rounded-lg border border-primary bg-primary/10 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/20 transition-colors flex items-center justify-center gap-2"
                >
                  <FileDown className="h-4 w-4" />
                  ダウンロード ({format.toUpperCase()})
                </button>
              </div>
            )}

            {result && result.status === 'failed' && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/5 p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <span className="text-sm text-red-700 dark:text-red-400">
                    生成に失敗しました
                  </span>
                </div>
              </div>
            )}

            {error && (
              <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/5 p-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <span className="text-sm text-red-700 dark:text-red-400">{error}</span>
                </div>
              </div>
            )}
          </div>

          {/* レポート種別説明 */}
          <div className="rounded-xl border border-border bg-card p-6">
            <h3 className="text-sm font-semibold text-card-foreground mb-3">
              レポート内容
            </h3>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>- リスクサマリー (全社概要)</li>
              <li>- リスクレベル別集計</li>
              <li>- 高リスク企業の詳細分析</li>
              <li>- アラート一覧</li>
              <li>- 推奨対応アクション</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
