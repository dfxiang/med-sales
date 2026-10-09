import { expect, test } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 针对运行中环境的界面回归：
 * 1) 商品管理列表展示分类名称（而不是分类主键）；
 * 2) 库存流水用商品选择器筛选（而不是手输商品 ID）。
 *
 * 这两个点都曾经是「代码已改、部署未重建」导致线上仍是旧界面，故放在 live 套件里守护。
 */
test.beforeEach(async ({ page }) => {
  await login(page)
})

test('商品管理：分类列显示分类名称', async ({ page }) => {
  await gotoMenu(page, '商品管理')
  await expect(page.locator('thead th').nth(3)).toHaveText('分类')
  const categoryCell = page.locator('tbody tr').first().locator('td').nth(3)
  await expect(categoryCell).not.toHaveText(/^\d*$/)
})

test('库存流水：商品筛选为选择控件并可筛选', async ({ page }) => {
  await gotoMenu(page, '库存流水')
  await expect(page.locator('.el-form-item').filter({ hasText: '商品 ID' })).toHaveCount(0)

  const filter = page.locator('[data-test="filter-product"]')
  await expect(filter).toBeVisible()
  await filter.click()
  await page.locator('.el-select-dropdown__item:visible').first().click()
  await page.getByTestId('btn-search').click()
  await expect(page.locator('tbody tr').first()).toBeVisible()
})
