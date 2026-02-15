/**
 * アプリケーション全体の状態管理
 * Zustand を使用したグローバルストア
 */

import { create } from 'zustand'

interface AppState {
  /** サイドバーの開閉状態 */
  sidebarOpen: boolean
  /** テーマ (dark/light) */
  theme: 'dark' | 'light'
  /** 選択中の企業ID */
  selectedCompanyId: string | null
  /** 分析実行中フラグ */
  isAnalysisRunning: boolean

  // アクション
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  toggleTheme: () => void
  setTheme: (theme: 'dark' | 'light') => void
  setSelectedCompanyId: (id: string | null) => void
  setAnalysisRunning: (running: boolean) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  selectedCompanyId: null,
  isAnalysisRunning: false,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleTheme: () =>
    set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
  setTheme: (theme) => set({ theme }),
  setSelectedCompanyId: (id) => set({ selectedCompanyId: id }),
  setAnalysisRunning: (running) => set({ isAnalysisRunning: running }),
}))
