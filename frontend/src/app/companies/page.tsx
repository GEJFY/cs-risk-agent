'use client'

import { CompanyTable } from '@/components/companies/company-table'
import { useAppStore } from '@/stores/app-store'
import { Building2, Download, Plus } from 'lucide-react'

/**
 * 企業一覧ページ
 * 連結子会社のリスクスコア付き一覧表を表示
 */
export default function CompaniesPage() {
  const { sidebarOpen } = useAppStore()

  return (
    <div
      className={`
        space-y-6 transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* ページヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary/10 p-2.5">
            <Building2 className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">企業一覧</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              連結子会社のリスクスコアと分析状況
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-1.5 rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
            <Download className="h-4 w-4" />
            エクスポート
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            <Plus className="h-4 w-4" />
            企業追加
          </button>
        </div>
      </div>

      {/* 企業テーブル */}
      <CompanyTable />
    </div>
  )
}
