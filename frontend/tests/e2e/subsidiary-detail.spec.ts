import { test, expect } from '@playwright/test'

test.describe('Subsidiary Detail Page', () => {
  test('should load subsidiary detail with risk score', async ({ page }) => {
    await page.goto('/subsidiaries/SUB-0006')

    // 上海子会社の名前が表示される (高リスク企業)
    await expect(page.getByText('东洋精密机械（上海）有限公司')).toBeVisible({ timeout: 15000 })

    // リスクスコアが表示される
    await expect(page.getByText('リスクスコア')).toBeVisible()
  })

  test('should display risk profile radar chart', async ({ page }) => {
    await page.goto('/subsidiaries/SUB-0003')

    // 建機リース子会社 (critical)
    await expect(page.getByText('東洋建機リース株式会社')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('リスクプロファイル')).toBeVisible()
  })

  test('should switch tabs', async ({ page }) => {
    await page.goto('/subsidiaries/SUB-0001')
    await expect(page.getByText('東洋エネルギーシステム')).toBeVisible({ timeout: 15000 })

    // リスク分析タブに切り替え
    await page.getByRole('button', { name: 'リスク分析' }).click()
    await expect(page.getByText('リスク所見一覧')).toBeVisible()

    // 履歴タブに切り替え
    await page.getByRole('button', { name: '履歴' }).click()
    await expect(page.getByText('分析履歴')).toBeVisible()
  })

  test('should show risk findings for high-risk entity', async ({ page }) => {
    await page.goto('/subsidiaries/SUB-0006')
    await expect(page.getByText('东洋精密机械')).toBeVisible({ timeout: 15000 })

    // リスク分析タブ
    await page.getByRole('button', { name: 'リスク分析' }).click()

    // アラート詳細が表示される
    await expect(page.getByText('アラート詳細')).toBeVisible({ timeout: 5000 })
  })
})
