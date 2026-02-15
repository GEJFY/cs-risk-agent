import { test, expect } from '@playwright/test'

test.describe('Companies Page', () => {
  test('should load companies list from API', async ({ page }) => {
    await page.goto('/companies')

    // テーブルが表示される
    await expect(page.getByText('東洋重工業株式会社')).toBeVisible({ timeout: 15000 })
  })

  test('should display subsidiary names', async ({ page }) => {
    await page.goto('/companies')

    // デモデータの子会社が表示される
    await expect(page.getByText('東洋エネルギーシステム')).toBeVisible({ timeout: 15000 })
  })

  test('should navigate to subsidiary detail', async ({ page }) => {
    await page.goto('/companies')

    // 子会社リンクをクリック
    const link = page.getByRole('link', { name: /東洋エネルギーシステム/ }).first()
    await expect(link).toBeVisible({ timeout: 15000 })
    await link.click()
    await expect(page).toHaveURL(/subsidiaries\/SUB-0001/)
  })
})
