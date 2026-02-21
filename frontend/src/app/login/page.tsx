'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAppStore } from '@/stores/app-store'
import { api } from '@/lib/api-client'
import { Shield, LogIn, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { setAuth } = useAppStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await api.auth.login(username, password)
      setAuth(res.access_token, username, res.role)
      router.push('/')
    } catch {
      setError('ログインに失敗しました。ユーザー名またはパスワードが正しくありません。')
    } finally {
      setLoading(false)
    }
  }

  const demoUsers = [
    { user: 'admin', role: 'Admin', desc: '全権限' },
    { user: 'auditor', role: 'Auditor', desc: '閲覧・分析・レポート' },
    { user: 'cfo', role: 'CFO', desc: '閲覧・分析・レポート' },
    { user: 'viewer', role: 'Viewer', desc: '閲覧のみ' },
  ]

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-md space-y-8 rounded-xl border border-border bg-card p-8 shadow-lg">
        {/* ヘッダー */}
        <div className="text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <h1 className="mt-4 text-2xl font-bold text-card-foreground">
            CS Risk Agent
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            連結子会社リスク分析システム
          </p>
        </div>

        {/* ログインフォーム */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-card-foreground">
              ユーザー名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="admin"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-card-foreground">
              パスワード
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              placeholder="admin"
              required
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            <LogIn className="h-4 w-4" />
            {loading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>

        {/* デモユーザー一覧 */}
        <div className="border-t border-border pt-4">
          <p className="mb-3 text-xs font-medium text-muted-foreground">
            デモユーザー（パスワード = ユーザー名）
          </p>
          <div className="grid grid-cols-2 gap-2">
            {demoUsers.map((u) => (
              <button
                key={u.user}
                type="button"
                onClick={() => {
                  setUsername(u.user)
                  setPassword(u.user)
                }}
                className="rounded-lg border border-border p-2 text-left hover:bg-accent/30 transition-colors"
              >
                <p className="text-xs font-medium text-card-foreground">
                  {u.user} ({u.role})
                </p>
                <p className="text-xs text-muted-foreground">{u.desc}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
