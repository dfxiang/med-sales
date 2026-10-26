import { expect, test } from '@playwright/test'

import { login } from '../e2e/helpers'

test.beforeEach(async ({ page }) => {
  await page.goto('/login')
  await page.evaluate(() => localStorage.clear())
  await page.reload()
})

test('登录页支持七种语言并持久化选择', async ({ page }) => {
  const language = page.getByTestId('language-switcher')
  await expect(language).toBeVisible()

  const locales = ['en', 'vi', 'ms', 'id', 'de', 'fr', 'zh-CN']
  const expectedHeadings = [
    'Pharmaceutical Sales Management',
    'Hệ thống quản lý bán thuốc',
    'Sistem Pengurusan Jualan Farmaseutikal',
    'Sistem Manajemen Penjualan Farmasi',
    'Pharmazeutisches Vertriebsmanagement',
    'Gestion des ventes pharmaceutiques',
    '医药销售管理系统',
  ]
  const localeNames: Record<string, string> = {
    en: 'English',
    vi: 'Tiếng Việt',
    ms: 'Bahasa Melayu',
    id: 'Bahasa Indonesia',
    de: 'Deutsch',
    fr: 'Français',
    'zh-CN': '中文',
  }

  for (const [index, locale] of locales.entries()) {
    await language.click()
    await page.getByText(localeNames[locale], { exact: true }).last().click()
    await expect(page.locator('html')).toHaveAttribute('lang', locale)
    await expect(page.locator('.login-title')).toHaveText(expectedHeadings[index])
  }

  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('lang', 'zh-CN')
})

test('浅色/深色主题可切换并在刷新后保留', async ({ page }) => {
  const toggle = page.getByTestId('theme-toggle')
  const original = await page.locator('html').getAttribute('data-theme')
  await toggle.click()
  const changed = original === 'dark' ? 'light' : 'dark'
  await expect(page.locator('html')).toHaveAttribute('data-theme', changed)
  if (changed === 'dark') await expect(page.locator('html')).toHaveClass(/(^|\s)dark(\s|$)/)
  else await expect(page.locator('html')).not.toHaveClass(/(^|\s)dark(\s|$)/)

  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', changed)
})

test('登录后顶栏语言与主题入口可用', async ({ page }) => {
  await login(page)
  await page.evaluate(() => {
    localStorage.setItem('medsales_locale', 'en')
    localStorage.setItem('medsales_theme', 'dark')
  })
  await page.reload()

  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByTestId('language-switcher')).toBeVisible()
  await expect(page.getByTestId('theme-toggle')).toBeVisible()
  await expect(page.locator('.header-title')).toHaveText('Business Dashboard')
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(7, 17, 22)')
  await expect(page.locator('.layout-main')).toHaveCSS('background-color', 'rgb(7, 17, 22)')

  await page.goto('/customers')
  await expect(page.locator('.header-title')).toHaveText('Customer Management')
  await expect(page.locator('thead th').filter({ hasText: 'Customer Name' })).toBeVisible()
})
