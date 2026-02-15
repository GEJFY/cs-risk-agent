import { test, expect } from '@playwright/test'

test.describe('Settings Page', () => {
  test('should load settings with provider status', async ({ page }) => {
    await page.goto('/settings')

    // AIプロバイダー設定が表示される
    await expect(page.getByText('AI プロバイダー設定')).toBeVisible({ timeout: 15000 })
  })

  test('should display provider cards', async ({ page }) => {
    await page.goto('/settings')

    // プロバイダーが表示される
    await expect(page.getByText('Azure AI Foundry')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText('AWS Bedrock')).toBeVisible()
  })

  test('should show budget information', async ({ page }) => {
    await page.goto('/settings')

    // 予算情報が表示される
    await expect(page.getByText(/予算/)).toBeVisible({ timeout: 15000 })
  })
})
