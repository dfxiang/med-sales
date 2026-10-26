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

test('浅色主题侧栏使用浅色表面并保留清晰的选中状态', async ({ page }) => {
  await login(page)
  await page.evaluate(() => localStorage.setItem('medsales_theme', 'light'))
  await page.reload()

  const aside = page.locator('.layout-aside')
  const activeItem = page.locator('.layout-aside .el-menu-item.is-active')
  await expect(aside).toHaveCSS('background-color', 'rgb(248, 250, 252)')
  await expect(activeItem).toHaveCSS('background-color', 'rgb(223, 241, 246)')
  await expect(activeItem).toHaveCSS('color', 'rgb(14, 100, 120)')

  await page.getByTestId('theme-toggle').click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(aside).toHaveCSS('background-color', 'rgb(7, 18, 24)')
})

test('页脚展示项目信息、GitHub 链接和微信并支持多语言', async ({ page }) => {
  await login(page)
  await page.setViewportSize({ width: 1280, height: 800 })

  const header = page.locator('.layout-header')
  const footer = page.getByTestId('layout-footer')
  const github = page.getByTestId('footer-github')
  await expect(footer).toBeVisible()
  await expect(github).toHaveAttribute('href', 'https://github.com/dfxiang/med-sales')
  await expect(github).not.toContainText('github.com/dfxiang/med-sales')
  await expect(page.getByTestId('footer-author')).toContainText('Danny Xiang, Wuhan, China')
  await expect(page.getByTestId('footer-wechat')).toContainText('4198166')

  const headerBox = await header.boundingBox()
  const footerBox = await footer.boundingBox()
  expect(footerBox?.height).toBe(52)
  expect(footerBox?.height ?? 0).toBeLessThan(headerBox?.height ?? 0)

  const localizedFooter = [
    ['en', 'Pharmaceutical Sales Management', 'Open-source repository', 'Author: Danny Xiang, Wuhan, China', 'WeChat:'],
    ['vi', 'Hệ thống quản lý bán thuốc', 'Kho mã nguồn mở', 'Tác giả: Danny Xiang, Wuhan, China', 'WeChat:'],
    ['ms', 'Sistem Pengurusan Jualan Farmaseutikal', 'Repositori sumber terbuka', 'Pengarang: Danny Xiang, Wuhan, China', 'WeChat:'],
    ['id', 'Sistem Manajemen Penjualan Farmasi', 'Repositori sumber terbuka', 'Penulis: Danny Xiang, Wuhan, China', 'WeChat:'],
    ['de', 'Pharmazeutisches Vertriebsmanagement', 'Open-Source-Repository', 'Autor: Danny Xiang, Wuhan, China', 'WeChat:'],
    ['fr', 'Gestion des ventes pharmaceutiques', 'Dépôt open source', 'Auteur : Danny Xiang, Wuhan, China', 'WeChat :'],
    ['zh-CN', '医药销售管理系统', 'GitHub 开源地址', '作者：Danny Xiang, Wuhan, China', '微信：'],
  ]
  for (const [locale, project, repositoryLabel, authorText, wechatLabel] of localizedFooter) {
    await page.evaluate((value) => localStorage.setItem('medsales_locale', value), locale)
    await page.reload()
    await expect(page.locator('.footer-project')).toHaveText(project)
    await expect(page.getByTestId('footer-github')).toContainText(repositoryLabel)
    await expect(page.getByTestId('footer-author')).toHaveText(authorText)
    await expect(page.getByTestId('footer-wechat')).toContainText(wechatLabel)
    await expect(page.getByTestId('layout-footer')).toBeInViewport()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  }
})
