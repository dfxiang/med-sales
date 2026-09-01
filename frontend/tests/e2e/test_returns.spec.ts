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

test('退货全流程：创建退货单 → 处理入库 → 库存增加', async ({ page }) => {
  // 先创建一笔销售订单作为退货来源
  await gotoMenu(page, '销售订单')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户', { type: 'select', value: '测试医院' })
  await fillFormField(page, '销售员', { type: 'select', value: '张三' })
  await fillFormField(page, '发货仓库', { type: 'select', value: '上海中心仓' })
  await fillFormField(page, '下单日期', { type: 'date', value: '2026-09-01' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 20)
  await submitDialog(page)
  const orderNo = (await page.locator('tbody tr').filter({ hasText: '待付款' }).first().locator('td').first().innerText()).trim()

  const before = await getInventoryQuantity(page)

  // 创建退货单
  await gotoMenu(page, '退货管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '原订单', { type: 'select', value: orderNo })
  await fillFormField(page, '退货日期', { type: 'date', value: '2026-09-03' })
  await fillFormField(page, '退货原因', { type: 'select', value: '质量问题' })
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 5)
  await submitDialog(page)

  const returnRow = page.locator('tbody tr').filter({ hasText: '待处理' }).first()
  await expect(returnRow).toBeVisible()

  // 处理入库
  await returnRow.getByRole('button', { name: '处理入库' }).click()
  await page.locator('.el-message-box').getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('tbody tr').filter({ hasText: '已完成' }).first()).toBeVisible()

  expect(await getInventoryQuantity(page)).toBe(before + 5)
})
