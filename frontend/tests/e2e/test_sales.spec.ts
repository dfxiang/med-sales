import { expect, test } from '@playwright/test'

import {
  fillFormField,
  fillItemNumber,
  getInventoryQuantity,
  gotoMenu,
  login,
  pickItemProduct,
  submitDialog,
} from './helpers'

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('销售全流程：下单 → 发货出库 → 库存扣减', async ({ page }) => {
  const before = await getInventoryQuantity(page)

  await gotoMenu(page, '销售订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户', { type: 'select', value: '测试医院' })
  await fillFormField(page, '销售员', { type: 'select', value: '张三' })
  await fillFormField(page, '发货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 10)
  await submitDialog(page)

  const orderRow = page.locator('tbody tr').filter({ hasText: '待付款' }).first()
  await expect(orderRow).toBeVisible()

  // 发货出库
  await orderRow.getByRole('button', { name: '发货' }).click()
  const shipDialog = page.locator('.el-dialog').filter({ visible: true }).first()
  await shipDialog.locator('input').first().fill('2026-09-02')
  await shipDialog.locator('input').first().press('Enter')
  await shipDialog.getByTestId('btn-ship-save').click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('tbody tr').filter({ hasText: '已发货' }).first()).toBeVisible()

  // 库存扣减 10
  expect(await getInventoryQuantity(page)).toBe(before - 10)
})

test('销售订单取消', async ({ page }) => {
  await gotoMenu(page, '销售订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户', { type: 'select', value: '测试医院' })
  await fillFormField(page, '销售员', { type: 'select', value: '张三' })
  await fillFormField(page, '发货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 5)
  await submitDialog(page)

  const orderNo = (await page.locator('tbody tr').filter({ hasText: '待付款' }).first().locator('td').first().innerText()).trim()
  const orderRow = page.locator('tbody tr').filter({ hasText: orderNo })
  await orderRow.getByRole('button', { name: '取消' }).click()
  await page.locator('.el-message-box').getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('tbody tr').filter({ hasText: orderNo }).filter({ hasText: '已取消' })).toBeVisible()
})

test('销售订单删除', async ({ page }) => {
  await gotoMenu(page, '销售订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户', { type: 'select', value: '测试医院' })
  await fillFormField(page, '销售员', { type: 'select', value: '张三' })
  await fillFormField(page, '发货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 5)
  await submitDialog(page)

  const orderNo = (await page.locator('tbody tr').filter({ hasText: '待付款' }).first().locator('td').first().innerText()).trim()
  const orderRow = page.locator('tbody tr').filter({ hasText: orderNo })
  await orderRow.getByRole('button', { name: '删除' }).click()
  await page.locator('.el-message-box').getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('tbody tr').filter({ hasText: orderNo })).toBeHidden()
})
