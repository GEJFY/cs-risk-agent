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
  /** 認証トークン */
  accessToken: string | null
  /** ユーザー名 */
  username: string | null
  /** ユーザーロール */
  userRole: string | null

  // アクション
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  toggleTheme: () => void
  setTheme: (theme: 'dark' | 'light') => void
  setSelectedCompanyId: (id: string | null) => void
  setAnalysisRunning: (running: boolean) => void
  setAuth: (token: string, username: string, role: string) => void
  clearAuth: () => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  selectedCompanyId: null,
  isAnalysisRunning: false,
  accessToken: typeof window !== 'undefined' ? localStorage.getItem('access_token') : null,
  username: typeof window !== 'undefined' ? localStorage.getItem('username') : null,
  userRole: typeof window !== 'undefined' ? localStorage.getItem('user_role') : null,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleTheme: () =>
    set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),
  setTheme: (theme) => set({ theme }),
  setSelectedCompanyId: (id) => set({ selectedCompanyId: id }),
  setAnalysisRunning: (running) => set({ isAnalysisRunning: running }),
  setAuth: (token, username, role) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token)
      localStorage.setItem('username', username)
      localStorage.setItem('user_role', role)
    }
    set({ accessToken: token, username, userRole: role })
  },
  clearAuth: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      localStorage.removeItem('user_role')
    }
    set({ accessToken: null, username: null, userRole: null })
  },
}))
