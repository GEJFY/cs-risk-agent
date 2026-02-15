import { create } from 'zustand'

/**
 * フィルターストア状態型定義
 */
interface FilterState {
  /** 会計年度 */
  fiscalYear: number
  /** 会計四半期 (1-4) */
  fiscalQuarter: number
  /** 業種コード */
  industryCode: string | null
  /** リスクレベル */
  riskLevel: string | null

  /** フィルター更新アクション */
  setFiscalYear: (year: number) => void
  setFiscalQuarter: (quarter: number) => void
  setIndustryCode: (code: string | null) => void
  setRiskLevel: (level: string | null) => void
  resetFilters: () => void
}

/** デフォルト値 */
const DEFAULT_FISCAL_YEAR = 2024
const DEFAULT_FISCAL_QUARTER = 4

/**
 * グローバルフィルターストア
 * Zustand によるクライアントサイドの状態管理
 */
export const useFilterStore = create<FilterState>((set) => ({
  fiscalYear: DEFAULT_FISCAL_YEAR,
  fiscalQuarter: DEFAULT_FISCAL_QUARTER,
  industryCode: null,
  riskLevel: null,

  setFiscalYear: (year: number) => set({ fiscalYear: year }),
  setFiscalQuarter: (quarter: number) => set({ fiscalQuarter: quarter }),
  setIndustryCode: (code: string | null) => set({ industryCode: code }),
  setRiskLevel: (level: string | null) => set({ riskLevel: level }),
  resetFilters: () =>
    set({
      fiscalYear: DEFAULT_FISCAL_YEAR,
      fiscalQuarter: DEFAULT_FISCAL_QUARTER,
      industryCode: null,
      riskLevel: null,
    }),
}))
