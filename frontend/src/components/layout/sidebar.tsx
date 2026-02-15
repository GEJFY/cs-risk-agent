'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Building2,
  PlayCircle,
  Settings,
  Shield,
  ChevronLeft,
} from 'lucide-react'
import { useAppStore } from '@/stores/app-store'

/** サイドバーナビゲーション項目 */
const navItems = [
  {
    href: '/',
    label: 'ダッシュボード',
    labelEn: 'Dashboard',
    icon: LayoutDashboard,
  },
  {
    href: '/companies',
    label: '企業一覧',
    labelEn: 'Companies',
    icon: Building2,
  },
  {
    href: '/analysis',
    label: '分析実行',
    labelEn: 'Analysis',
    icon: PlayCircle,
  },
  {
    href: '/settings',
    label: '設定',
    labelEn: 'Settings',
    icon: Settings,
  },
]

/**
 * サイドバーナビゲーション
 * ページ間の移動と現在地表示を管理
 */
export function Sidebar() {
  const pathname = usePathname()
  const { sidebarOpen, toggleSidebar } = useAppStore()

  return (
    <aside
      className={`
        fixed left-0 top-0 z-40 h-screen border-r border-border
        bg-card transition-all duration-300 ease-in-out
        ${sidebarOpen ? 'w-64' : 'w-16'}
      `}
    >
      {/* ロゴエリア */}
      <div className="flex h-16 items-center justify-between border-b border-border px-4">
        <div className="flex items-center gap-2 overflow-hidden">
          <Shield className="h-7 w-7 shrink-0 text-primary" />
          {sidebarOpen && (
            <span className="whitespace-nowrap text-lg font-bold text-foreground">
              CS Risk Agent
            </span>
          )}
        </div>
        <button
          onClick={toggleSidebar}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          aria-label={sidebarOpen ? 'サイドバーを閉じる' : 'サイドバーを開く'}
        >
          <ChevronLeft
            className={`h-5 w-5 transition-transform duration-300 ${
              !sidebarOpen ? 'rotate-180' : ''
            }`}
          />
        </button>
      </div>

      {/* ナビゲーションリンク */}
      <nav className="mt-4 flex flex-col gap-1 px-2">
        {navItems.map((item) => {
          const isActive =
            item.href === '/'
              ? pathname === '/'
              : pathname.startsWith(item.href)
          const Icon = item.icon

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                group flex items-center gap-3 rounded-lg px-3 py-2.5
                text-sm font-medium transition-colors
                ${
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }
              `}
              title={!sidebarOpen ? item.label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {sidebarOpen && (
                <span className="whitespace-nowrap">{item.label}</span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* サイドバー下部の情報 */}
      {sidebarOpen && (
        <div className="absolute bottom-4 left-0 right-0 px-4">
          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <p className="text-xs text-muted-foreground">
              連結子会社リスク分析ツール
            </p>
            <p className="mt-1 text-xs text-muted-foreground">v0.1.0</p>
          </div>
        </div>
      )}
    </aside>
  )
}
