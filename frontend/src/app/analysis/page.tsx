'use client'

import { useState, useEffect } from 'react'
import { AnalysisForm } from '@/components/analysis/analysis-form'
import { useAppStore } from '@/stores/app-store'
import { fetchAPI } from '@/lib/api-client'
import { PlayCircle, History, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'

/** タスク履歴 */
interface TaskHistory {
  task_id: string
  status: string
  progress: number
  company_count: number
  engines: string[]
  fiscal_year: number
  created_at: string
  completed_at: string | null
  result_count: number
  error: string | null
}

/**
 * 分析実行ページ
 * 企業を選択して各種リスク分析を実行
 */
export default function AnalysisPage() {
  const { sidebarOpen } = useAppStore()
  const [taskHistory, setTaskHistory] = useState<TaskHistory[]>([])

  /** タスク履歴取得 */
  useEffect(() => {
    fetchAPI<{ tasks: TaskHistory[] }>('/api/v1/analysis/tasks?limit=10')
      .then((data) => setTaskHistory(data.tasks))
      .catch(() => {})
  }, [])

  const statusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-primary" />
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />
    }
  }

  return (
    <div
      className={`
        space-y-6 transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* ページヘッダー */}
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-primary/10 p-2.5">
          <PlayCircle className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">分析実行</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            AI を活用した連結子会社リスク分析
          </p>
        </div>
      </div>

      {/* 分析フォーム */}
      <AnalysisForm />

      {/* 分析履歴 */}
      {taskHistory.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-6">
          <div className="mb-4 flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            <h3 className="text-base font-semibold text-card-foreground">
              分析タスク履歴
            </h3>
          </div>

          <div className="space-y-3">
            {taskHistory.map((task) => (
              <div
                key={task.task_id}
                className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-accent/30 transition-colors"
              >
                <div className="flex items-center gap-4">
                  {statusIcon(task.status)}
                  <div>
                    <p className="text-sm font-medium text-card-foreground">
                      {task.company_count}社 - {task.engines.join(', ')}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      FY{task.fiscal_year} | {task.result_count}件の結果
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">
                    {new Date(task.created_at).toLocaleString('ja-JP')}
                  </p>
                  <p className="text-xs font-mono text-muted-foreground">
                    {task.task_id.slice(0, 8)}...
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
