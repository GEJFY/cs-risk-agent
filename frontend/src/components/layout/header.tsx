'use client'

import { Bell, Moon, Sun, User } from 'lucide-react'
import { useAppStore } from '@/stores/app-store'

/**
 * ヘッダーコンポーネント
 * ページタイトル、テーマ切替、通知、ユーザーエリアを表示
 */
export function Header() {
  const { theme, toggleTheme, sidebarOpen } = useAppStore()

  return (
    <header
      className={`
        sticky top-0 z-30 flex h-16 items-center justify-between
        border-b border-border bg-card/80 backdrop-blur-sm px-6
        transition-all duration-300
        ${sidebarOpen ? 'ml-64' : 'ml-16'}
      `}
    >
      {/* 左側: ページタイトル */}
      <div>
        <h2 className="text-lg font-semibold text-foreground">
          CS Risk Agent
        </h2>
        <p className="text-xs text-muted-foreground">
          連結子会社リスク分析ツール
        </p>
      </div>

      {/* 右側: アクションエリア */}
      <div className="flex items-center gap-2">
        {/* テーマ切替 */}
        <button
          onClick={toggleTheme}
          className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          aria-label="テーマ切替"
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
        </button>

        {/* 通知ベル */}
        <button
          className="relative rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          aria-label="通知"
        >
          <Bell className="h-5 w-5" />
          {/* 未読通知バッジ */}
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-risk-critical" />
        </button>

        {/* ユーザーアバター */}
        <div className="ml-2 flex items-center gap-2 rounded-lg border border-border px-3 py-1.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-foreground">管理者</p>
            <p className="text-xs text-muted-foreground">admin</p>
          </div>
        </div>
      </div>
    </header>
  )
}
