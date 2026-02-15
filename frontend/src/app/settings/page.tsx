'use client'

import { useAppStore } from '@/stores/app-store'
import {
  Settings,
  Brain,
  DollarSign,
  Bell,
  Shield,
  CheckCircle,
  XCircle,
  AlertCircle,
} from 'lucide-react'
import type { AIProviderConfig } from '@/types'

/** デモ用AIプロバイダー設定 */
const mockAIProviders: AIProviderConfig[] = [
  {
    provider: 'OpenAI',
    model: 'GPT-4o',
    status: 'active',
    apiKeyConfigured: true,
    monthlyBudget: 500,
    monthlyUsage: 127.5,
    lastUsed: '2026-02-15T10:30:00Z',
  },
  {
    provider: 'Anthropic',
    model: 'Claude 3.5 Sonnet',
    status: 'active',
    apiKeyConfigured: true,
    monthlyBudget: 300,
    monthlyUsage: 89.2,
    lastUsed: '2026-02-15T09:15:00Z',
  },
  {
    provider: 'Azure OpenAI',
    model: 'GPT-4o (Azure)',
    status: 'inactive',
    apiKeyConfigured: false,
    monthlyBudget: 0,
    monthlyUsage: 0,
  },
]

/** ステータスの表示設定 */
const statusConfig = {
  active: {
    icon: CheckCircle,
    label: '稼働中',
    colorClass: 'text-risk-low',
    bgClass: 'bg-risk-low/10',
  },
  inactive: {
    icon: XCircle,
    label: '未設定',
    colorClass: 'text-muted-foreground',
    bgClass: 'bg-muted',
  },
  error: {
    icon: AlertCircle,
    label: 'エラー',
    colorClass: 'text-risk-critical',
    bgClass: 'bg-risk-critical/10',
  },
}

/**
 * 設定ページ
 * AIプロバイダーの状態、予算情報、通知設定を表示
 */
export default function SettingsPage() {
  const { sidebarOpen } = useAppStore()

  /** 予算合計 */
  const totalBudget = mockAIProviders.reduce(
    (sum, p) => sum + p.monthlyBudget,
    0
  )
  const totalUsage = mockAIProviders.reduce(
    (sum, p) => sum + p.monthlyUsage,
    0
  )
  const usagePct = totalBudget > 0 ? (totalUsage / totalBudget) * 100 : 0

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
          <Settings className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground">設定</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            AIプロバイダーとシステム設定の管理
          </p>
        </div>
      </div>

      {/* 予算サマリー */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <DollarSign className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            月間予算
          </h3>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <p className="text-sm text-muted-foreground">月間予算総額</p>
            <p className="text-2xl font-bold text-card-foreground">
              ${totalBudget.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">今月の使用額</p>
            <p className="text-2xl font-bold text-card-foreground">
              ${totalUsage.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">使用率</p>
            <p className="text-2xl font-bold text-card-foreground">
              {usagePct.toFixed(1)}%
            </p>
          </div>
        </div>

        <div className="mt-4">
          <div className="h-3 w-full rounded-full bg-muted">
            <div
              className={`h-3 rounded-full transition-all ${
                usagePct > 80
                  ? 'bg-risk-critical'
                  : usagePct > 50
                    ? 'bg-risk-medium'
                    : 'bg-risk-low'
              }`}
              style={{ width: `${Math.min(usagePct, 100)}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            残り予算: ${(totalBudget - totalUsage).toFixed(2)}
          </p>
        </div>
      </div>

      {/* AIプロバイダー設定 */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Brain className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            AIプロバイダー
          </h3>
        </div>

        <div className="space-y-4">
          {mockAIProviders.map((provider) => {
            const config = statusConfig[provider.status]
            const StatusIcon = config.icon
            const providerUsagePct =
              provider.monthlyBudget > 0
                ? (provider.monthlyUsage / provider.monthlyBudget) * 100
                : 0

            return (
              <div
                key={provider.provider}
                className="rounded-lg border border-border p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-sm font-bold text-muted-foreground">
                      {provider.provider.charAt(0)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-card-foreground">
                        {provider.provider}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        モデル: {provider.model}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${config.bgClass} ${config.colorClass}`}
                  >
                    <StatusIcon className="h-3 w-3" />
                    {config.label}
                  </span>
                </div>

                {provider.status === 'active' && (
                  <div className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4 sm:grid-cols-4">
                    <div>
                      <p className="text-xs text-muted-foreground">APIキー</p>
                      <p className="text-sm font-medium text-risk-low">設定済み</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">月間予算</p>
                      <p className="text-sm font-medium text-card-foreground">
                        ${provider.monthlyBudget}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">今月使用額</p>
                      <p className="text-sm font-medium text-card-foreground">
                        ${provider.monthlyUsage.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">使用率</p>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 flex-1 rounded-full bg-muted">
                          <div
                            className="h-1.5 rounded-full bg-primary"
                            style={{
                              width: `${Math.min(providerUsagePct, 100)}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {providerUsagePct.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {provider.status === 'inactive' && (
                  <div className="mt-4 border-t border-border pt-4">
                    <button className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
                      設定する
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* 通知設定 */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            通知設定
          </h3>
        </div>

        <div className="space-y-4">
          {[
            {
              label: 'クリティカルリスクアラート',
              description: 'リスクスコア80以上の検出時に通知',
              enabled: true,
            },
            {
              label: '分析完了通知',
              description: 'リスク分析の完了時に通知',
              enabled: true,
            },
            {
              label: '日次サマリーレポート',
              description: '毎日のリスク状況サマリーを送信',
              enabled: false,
            },
            {
              label: '予算アラート',
              description: 'AI使用料が予算の80%を超えた場合に通知',
              enabled: true,
            },
          ].map((setting) => (
            <div
              key={setting.label}
              className="flex items-center justify-between rounded-lg border border-border p-4"
            >
              <div>
                <p className="text-sm font-medium text-card-foreground">
                  {setting.label}
                </p>
                <p className="text-xs text-muted-foreground">
                  {setting.description}
                </p>
              </div>
              <div
                className={`
                  relative h-6 w-11 cursor-pointer rounded-full transition-colors
                  ${setting.enabled ? 'bg-primary' : 'bg-muted'}
                `}
              >
                <div
                  className={`
                    absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform
                    ${setting.enabled ? 'translate-x-5' : 'translate-x-0.5'}
                  `}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* リスク閾値設定 */}
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="mb-4 flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-card-foreground">
            リスク閾値設定
          </h3>
        </div>

        <p className="mb-4 text-sm text-muted-foreground">
          リスクレベルの判定に使用するスコア閾値を設定
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            {
              level: 'クリティカル',
              threshold: 80,
              color: 'border-risk-critical',
              textColor: 'text-risk-critical',
            },
            {
              level: '高リスク',
              threshold: 60,
              color: 'border-risk-high',
              textColor: 'text-risk-high',
            },
            {
              level: '中リスク',
              threshold: 40,
              color: 'border-risk-medium',
              textColor: 'text-risk-medium',
            },
          ].map((item) => (
            <div
              key={item.level}
              className={`rounded-lg border-l-4 ${item.color} border border-border p-4`}
            >
              <p className={`text-sm font-medium ${item.textColor}`}>
                {item.level}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="number"
                  defaultValue={item.threshold}
                  min={0}
                  max={100}
                  className="w-20 rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <span className="text-sm text-muted-foreground">以上</span>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex justify-end">
          <button className="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
            設定を保存
          </button>
        </div>
      </div>
    </div>
  )
}
