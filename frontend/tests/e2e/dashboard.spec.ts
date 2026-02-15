import { test, expect } from '@playwright/test'

test.describe('Dashboard Page', () => {
  test('should load dashboard with risk summary', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/CS Risk Agent/)

    // リスクサマリーカードが表示される
    await expect(page.getByText('対象子会社数')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('平均リスクスコア')).toBeVisible()
    await expect(page.getByText('要注意アラート')).toBeVisible()
  })

  test('should display risk level breakdown', async ({ page }) => {
    await page.goto('/')
    // リスクレベル分布が表示される
    await expect(page.getByText('リスクレベル分布')).toBeVisible({ timeout: 15000 })
  })

  test('should navigate to companies page', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /子会社/i }).first().click()
    await expect(page).toHaveURL(/companies/)
  })
})
