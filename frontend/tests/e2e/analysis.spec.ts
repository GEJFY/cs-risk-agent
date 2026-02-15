import { test, expect } from '@playwright/test'

test.describe('Analysis Page', () => {
  test('should load analysis page with company selector', async ({ page }) => {
    await page.goto('/analysis')

    // 分析フォームが表示される
    await expect(page.getByText('リスク分析実行')).toBeVisible({ timeout: 15000 })
  })

  test('should display company options from API', async ({ page }) => {
    await page.goto('/analysis')

    // 企業選択ドロップダウンが表示される
    await expect(page.getByText('対象企業')).toBeVisible({ timeout: 15000 })
  })
})
