import { expect, test } from '@playwright/test'

import {
  fillFormField,
  fillItemNumber,
  gotoMenu,
  login,
  pickItemProduct,
  submitDialog,
} from './helpers'

test.beforeEach(async ({ page }) => {
  await login(page)
})

async function createOrder(page: import('@playwright/test').Page, settlement = '现款') {
  await gotoMenu(page, '销售订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户', { type: 'select', value: '测试医院' })
  await fillFormField(page, '销售员', { type: 'select', value: '张三' })
  await fillFormField(page, '发货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await fillFormField(page, '结算方式', { type: 'select', value: settlement })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 10)
  await submitDialog(page)
  return (await page.locator('tbody tr').filter({ hasText: '待付款' }).first().locator('td').first().innerText()).trim()
}

test('收款登记：订单收款后完成', async ({ page }) => {
  await createOrder(page)
  await gotoMenu(page, '收款记录')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '订单', { type: 'select', value: 'SO20260901' })
  await fillFormField(page, '付款日期', { type: 'date', value: '2026-09-05' })
  await fillFormField(page, '付款方式', { type: 'select', value: '银行转账' })
  await submitDialog(page)

  await expect(page.locator('tbody tr').filter({ hasText: '150.00' }).first()).toBeVisible()

  // 订单应变为已完成
  await gotoMenu(page, '销售订单')
  await expect(page.locator('tbody tr').filter({ hasText: '已完成' }).first()).toBeVisible()
})

test('应收账龄：未结订单展示应收金额', async ({ page }) => {
  await createOrder(page, '月结30天')
  await gotoMenu(page, '应收账龄')
  const row = page.locator('tbody tr').filter({ hasText: '测试医院' }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText('150.00')
})
