import { expect, test } from '@playwright/test'

import {
  fillItemNumber,
  getInventoryQuantity,
  gotoMenu,
  login,
  pickItemProduct,
  pickVisibleOption,
} from './helpers'

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('库存查询：展示商品库存与状态', async ({ page }) => {
  await gotoMenu(page, '库存查询')
  const row = page.locator('tbody tr').filter({ hasText: 'SKU-E2E-001' }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText('测试药品')
  await expect(row).toContainText('库存充足')
})

test('库存流水：展示期初入库流水并可筛选', async ({ page }) => {
  await gotoMenu(page, '库存流水')
  await expect(page.locator('tbody tr').filter({ hasText: '期初入库' }).first()).toBeVisible()
  await page.getByTestId('btn-search').click()
  await expect(page.locator('tbody tr').first()).toBeVisible()

  // 商品筛选为选择控件（值为 product_id，展示：名称（SKU）），表格同样展示名称
  await page.locator('[data-test="filter-product"]').click()
  await page
    .locator('.el-select-dropdown__item:visible')
    .filter({ hasText: 'SKU-E2E-001' })
    .first()
    .click()
  await page.getByTestId('btn-search').click()
  await expect(page.locator('tbody tr').first()).toContainText('测试药品（SKU-E2E-001）')
})

test('期初建账：入库后库存增加', async ({ page }) => {
  const before = await getInventoryQuantity(page)
  await gotoMenu(page, '期初建账')
  await page.locator('.el-form-item').filter({ hasText: '仓库' }).first().locator('.el-select').click()
  await pickVisibleOption(page, '上海中心仓')
  const dateItem = page.locator('.el-form-item').filter({ hasText: '入库日期' }).first()
  await dateItem.locator('input').first().fill('2026-09-01')
  await dateItem.locator('input').first().press('Enter')
  await pickItemProduct(page, 0, 'SKU-E2E-001')
  await fillItemNumber(page, 0, 500)
  await page.getByTestId('btn-submit').click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
  expect(await getInventoryQuantity(page)).toBe(before + 500)
})
