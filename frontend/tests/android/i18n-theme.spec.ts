import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => localStorage.clear())
  await page.reload()
})

test('Android 界面支持语言切换且没有横向溢出', async ({ page }) => {
  for (const locale of ['en', 'vi', 'ms', 'id', 'de', 'fr', 'zh-CN']) {
    await page.getByTestId('language-switcher').last().click()
    await page.getByTestId(`locale-${locale}`).click()
    await expect(page.locator('html')).toHaveAttribute('lang', locale)

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  }
  await expect(page.locator('.login-headline')).toHaveText('登录工作台')
})

test('Android 界面支持浅色与深色主题切换', async ({ page }) => {
  await page.getByTestId('theme-toggle').last().click()
  const theme = await page.locator('html').getAttribute('data-theme')
  expect(theme).toBe('dark')
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(7, 26, 32)')

  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})
