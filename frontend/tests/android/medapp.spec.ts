import { expect, test, type Page } from '@playwright/test'

async function login(page: Page) {
  await page.goto('/')
  await expect(page.getByTestId('username')).toBeVisible()
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/#\/home/, { timeout: 30_000 })
  await expect(page.locator('.hero-card')).toBeVisible()
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(overflow).toBeLessThanOrEqual(1)
}

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => localStorage.clear())
})

test('登录页可在手机视口使用，并能连接运行中的后端', async ({ page }) => {
  await page.reload()
  await expect(page.getByRole('heading', { name: 'medapp' })).toBeVisible()
  await expect(page.getByTestId('server-url')).toHaveValue('http://127.0.0.1:8001')
  await expectNoHorizontalOverflow(page)

  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByRole('button', { name: '显示密码' }).click()
  await expect(page.getByTestId('password')).toHaveAttribute('type', 'text')
  await page.getByRole('button', { name: '隐藏密码' }).click()
  await expect(page.getByTestId('password')).toHaveAttribute('type', 'password')
  await expectNoHorizontalOverflow(page)
})

test('经营首页展示真实汇总、五个主导航与无需横向滚动', async ({ page }) => {
  await login(page)
  await expect(page.locator('.hero-value')).not.toHaveText(/¥0$/)
  await expect(page.locator('.bottom-nav .nav-item')).toHaveCount(5)
  await expect(page.getByRole('link', { name: '首页' })).toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('heading', { name: '最近订单' })).toBeVisible()
  await expect(page.locator('.list-card .list-row').first()).toBeVisible()
  await expect(page.locator('.bar-chart .bar-column')).toHaveCount(6)
  await expectNoHorizontalOverflow(page)
})

test('销售订单支持服务端分页、订单号搜索与客户选择', async ({ page }) => {
  await login(page)
  await page.locator('.bottom-nav').getByRole('link', { name: '销售', exact: true }).click()
  await expect(page).toHaveURL(/#\/sales$/)
  await expect(page.locator('.order-card').first()).toBeVisible()
  await expect(page.locator('.pager-page')).toContainText('1/')

  const firstPageOrder = (await page.locator('.order-card .card-code').first().innerText()).trim()
  await page.locator('.order-card').first().click()
  await expect(page.locator('.detail-hero')).toBeVisible()
  await expect(page.getByRole('heading', { name: '订单详情' }).first()).toBeVisible()
  await page.getByRole('button', { name: '返回' }).click()
  await expect(page).toHaveURL(/#\/sales$/)

  await page.getByRole('button', { name: '下一页' }).click()
  await expect(page.locator('.pager-page')).toContainText('2/')
  await expect(page.locator('.order-card .card-code').first()).not.toHaveText(firstPageOrder)

  await page.locator('.pager-size').selectOption('10')
  await expect(page.locator('.pager-page')).toContainText('1/')
  await expect(page.locator('.order-card')).toHaveCount(10)

  await page.getByTestId('filter-order-no').fill(firstPageOrder.slice(-6))
  await page.getByTestId('btn-search').click()
  await expect(page.locator('.order-card').first()).toBeVisible()
  await expect(page.locator('.order-card .card-code').first()).toContainText(firstPageOrder.slice(-6))

  await page.getByRole('button', { name: /选择客户/ }).click()
  const search = page.getByRole('textbox', { name: '检索选择客户' })
  await expect(search).toBeVisible()
  await search.fill('天津')
  await expect(page.locator('.picker-option').first()).toBeVisible()
  await page.locator('.picker-option').first().click()
  await expect(page.getByText(/客户：天津/)).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('库存与 GSP 页面接通服务端并保持移动端布局', async ({ page }) => {
  await login(page)
  await page.locator('.bottom-nav').getByRole('link', { name: '库存', exact: true }).click()
  await expect(page).toHaveURL(/#\/inventory$/)
  await expect(page.locator('.inventory-card').first()).toBeVisible()
  await expect(page.locator('.pager-size')).toHaveValue('20')
  await expectNoHorizontalOverflow(page)

  await page.locator('.bottom-nav').getByRole('link', { name: '合规', exact: true }).click()
  await expect(page).toHaveURL(/#\/compliance$/)
  await expect(page.getByRole('heading', { name: 'GSP 合规' }).first()).toBeVisible()
  await expect(page.locator('.compliance-stat')).toHaveCount(4)
  await expectNoHorizontalOverflow(page)
})

test('待付款订单展示可执行操作，新建订单表单可进入', async ({ page }) => {
  await login(page)
  await page.locator('.bottom-nav').getByRole('link', { name: '销售', exact: true }).click()
  await page.getByRole('button', { name: '待付款', exact: true }).click()
  await expect(page.locator('.order-card .status').first()).toHaveText('待付款')
  await page.locator('.order-card').first().click()
  await expect(page.getByRole('button', { name: /发货/ })).toBeVisible()
  await expect(page.getByRole('button', { name: '取消订单' })).toBeVisible()

  await page.goto('/#/sales/new')
  await expect(page.getByRole('heading', { name: '新建销售单' }).first()).toBeVisible()
  await expect(page.getByRole('button', { name: /选择客户/ })).toBeVisible()
  await expect(page.getByTestId('create-order-submit')).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('我的页面展示账号权限、服务器与退出入口', async ({ page }) => {
  await login(page)
  await page.getByRole('link', { name: '我的' }).click()
  await expect(page).toHaveURL(/#\/profile$/)
  await expect(page.getByText('管理员', { exact: true })).toBeVisible()
  await expect(page.getByText('http://127.0.0.1:8001', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /退出登录/ })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('深色模式、减少动效和 44px 触控目标检查', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' })
  await login(page)
  const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor)
  expect(background).toBe('rgb(7, 26, 32)')

  const undersized = await page.locator('button:visible, a:visible, select:visible').evaluateAll(
    (nodes) =>
      nodes
        .map((node) => {
          const box = node.getBoundingClientRect()
          return {
            text: (node.textContent || node.getAttribute('aria-label') || '').trim().slice(0, 40),
            width: Math.round(box.width),
            height: Math.round(box.height),
          }
        })
        .filter((item) => item.width < 44 || item.height < 44),
  )
  expect(undersized).toEqual([])
  await expectNoHorizontalOverflow(page)
})
