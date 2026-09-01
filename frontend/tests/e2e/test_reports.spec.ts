import { expect, request as pwRequest, test } from '@playwright/test'

import { seed } from './global-setup'
import { gotoMenu, login } from './helpers'

test.beforeAll(async () => {
  // 报表依赖销售数据：通过 API 预置一笔订单，保证测试可独立运行
  const ids = seed()
  const ctx = await pwRequest.newContext({ baseURL: 'http://127.0.0.1:8002' })
  const loginResp = await ctx.post('/api/auth/login', { data: { username: 'admin', password: 'admin123' } })
  const token = (await loginResp.json()).access_token
  const resp = await ctx.post('/api/sales-orders', {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      customer_id: ids.custId,
      employee_id: ids.empId,
      warehouse_id: ids.whId,
      order_date: '2026-09-01',
      settlement_method: '月结30天',
      items: [{ product_id: ids.prodId, quantity: 10, discount_rate: 0 }],
    },
  })
  if (!resp.ok()) {
    throw new Error(`报表种子订单创建失败: ${resp.status()} ${await resp.text()}`)
  }
  await ctx.dispose()
})

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('销售报表：日/月汇总表格与图表展示', async ({ page }) => {
  await gotoMenu(page, '销售报表')
  await expect(page.getByTestId('daily-card')).toBeVisible()
  await expect(page.getByTestId('monthly-card')).toBeVisible()
  await expect(page.locator('.chart canvas').first()).toBeVisible()
  await expect(page.locator('.el-table__row').first()).toBeVisible()
})

test('客户汇总：展示客户销售数据', async ({ page }) => {
  await gotoMenu(page, '客户汇总')
  await expect(page.locator('tbody tr').filter({ hasText: '测试医院' }).first()).toBeVisible()
})

test('销售员业绩：展示员工销售数据', async ({ page }) => {
  await gotoMenu(page, '销售员业绩')
  await expect(page.locator('tbody tr').filter({ hasText: '张三' }).first()).toBeVisible()
})

test('商品汇总：展示商品销售数据', async ({ page }) => {
  await gotoMenu(page, '商品汇总')
  await expect(page.locator('tbody tr').filter({ hasText: '测试药品' }).first()).toBeVisible()
})

test('订单明细：展示并可筛选', async ({ page }) => {
  await gotoMenu(page, '订单明细')
  await expect(page.locator('.el-table__row').filter({ hasText: '测试医院' }).first()).toBeVisible()
  await page.getByTestId('btn-search').click()
  await expect(page.locator('.el-table__row').filter({ hasText: '测试医院' }).first()).toBeVisible()
})

test('库存状态报表：展示库存数据', async ({ page }) => {
  await gotoMenu(page, '库存状态')
  await expect(page.locator('tbody tr').filter({ hasText: 'SKU-E2E-001' }).first()).toBeVisible()
})

test('经营看板：展示统计卡片与月度图表', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page.getByTestId('dashboard')).toBeVisible()
  await expect(page.getByText('今日销售额')).toBeVisible()
  await expect(page.getByTestId('dashboard-chart')).toBeVisible()
  await expect(page.locator('.chart canvas').first()).toBeVisible()
})
