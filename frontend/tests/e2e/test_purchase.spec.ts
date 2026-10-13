import { expect, test } from '@playwright/test'

import {
  fillDialogInput,
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

test('采购全流程：创建采购单 → 收货 → 库存增加 → 状态完成', async ({ page }) => {
  const before = await getInventoryQuantity(page)

  await gotoMenu(page, '采购订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '供应商', { type: 'select', value: '测试供应商' })
  await fillFormField(page, '收货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 100)
  await page.locator('.items-table tbody tr').nth(0).locator('.el-input-number input').nth(1).fill('9')
  await submitDialog(page)

  // 列表中应出现待收货的采购单
  const orderRow = page.locator('tbody tr').filter({ hasText: '测试供应商' }).filter({ hasText: '待收货' }).first()
  await expect(orderRow).toBeVisible()

  // 收货
  await orderRow.getByRole('button', { name: '收货' }).click()
  const receiveDialog = page.locator('.el-dialog').filter({ visible: true }).first()
  await receiveDialog.locator('.el-input-number input').fill('100')
  await receiveDialog.getByTestId('btn-receive-save').click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })

  // 状态变为已完成
  await expect(page.locator('tbody tr').filter({ hasText: '已完成' }).first()).toBeVisible()

  // 库存增加 100
  expect(await getInventoryQuantity(page)).toBe(before + 100)
})

test('采购单删除：待收货状态可删除', async ({ page }) => {
  await gotoMenu(page, '采购订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '供应商', { type: 'select', value: '测试供应商' })
  await fillFormField(page, '收货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 10)
  await page.locator('.items-table tbody tr').nth(0).locator('.el-input-number input').nth(1).fill('9')
  await submitDialog(page)

  const orderRow = page.locator('tbody tr').filter({ hasText: '待收货' }).first()
  await orderRow.getByRole('button', { name: '删除' }).click()
  await page.locator('.el-message-box').getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
  await expect(orderRow).toBeHidden()
})
