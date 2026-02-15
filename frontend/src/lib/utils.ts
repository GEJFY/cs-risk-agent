import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/**
 * Tailwind CSSクラスの結合ユーティリティ
 * clsx で条件付きクラスを結合し、tailwind-merge で重複を解決する
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/**
 * 通貨フォーマット（日本円）
 * @param value - 金額（百万円単位など）
 * @param unit - 単位文字列
 * @returns フォーマット済み文字列
 */
export function formatCurrency(
  value: number,
  unit: string = '百万円'
): string {
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}兆${unit === '百万円' ? '' : unit}`
  }
  if (value >= 10_000) {
    return `${(value / 10_000).toFixed(1)}億${unit === '百万円' ? '' : unit}`
  }
  return `${value.toLocaleString('ja-JP')}${unit}`
}

/**
 * パーセンテージフォーマット
 * @param value - 数値（0-100 または 0-1）
 * @param decimals - 小数点以下桁数
 * @param isRatio - true の場合 value を100倍する
 * @returns フォーマット済み文字列
 */
export function formatPercent(
  value: number,
  decimals: number = 1,
  isRatio: boolean = false
): string {
  const pct = isRatio ? value * 100 : value
  return `${pct.toFixed(decimals)}%`
}

/**
 * リスクレベルに対応するテキストカラークラスを返す
 * @param level - リスクレベル (critical/high/medium/low)
 * @returns Tailwind テキストカラークラス
 */
export function riskLevelColor(
  level: 'critical' | 'high' | 'medium' | 'low' | string
): string {
  switch (level) {
    case 'critical':
      return 'text-risk-critical'
    case 'high':
      return 'text-risk-high'
    case 'medium':
      return 'text-risk-medium'
    case 'low':
      return 'text-risk-low'
    default:
      return 'text-muted-foreground'
  }
}

/**
 * リスクレベルに対応するバッジカラークラスを返す
 * @param level - リスクレベル (critical/high/medium/low)
 * @returns Tailwind バッジカラークラス群
 */
export function riskLevelBadgeColor(
  level: 'critical' | 'high' | 'medium' | 'low' | string
): string {
  switch (level) {
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'high':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'low':
      return 'bg-green-100 text-green-800 border-green-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

/**
 * リスクレベルの日本語ラベル
 */
export function riskLevelLabel(
  level: 'critical' | 'high' | 'medium' | 'low' | string
): string {
  switch (level) {
    case 'critical':
      return '重大'
    case 'high':
      return '高'
    case 'medium':
      return '中'
    case 'low':
      return '低'
    default:
      return '不明'
  }
}

/**
 * スコアからリスクレベルを判定
 * @param score - リスクスコア (0-100)
 * @returns リスクレベル文字列
 */
export function scoreToRiskLevel(
  score: number
): 'critical' | 'high' | 'medium' | 'low' {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}
