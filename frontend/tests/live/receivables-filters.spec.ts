import { expect, test } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 应收账龄查询条件（运行环境回归）：只看逾期、结算方式、截止日期、客户。
 * 列顺序：客户 / 订单号 / 下单日期 / 应收 / 已收 / 未收 / 结算方式 / 逾期天数。
 */
const bodyRow = '.el-table__body-wrapper tbody tr'

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('应收账龄：查询条件齐全且只看逾期生效', async ({ page }) => {
  await gotoMenu(page, '应收账龄')
  for (const testId of ['filter-customer', 'filter-as-of', 'filter-settlement', 'filter-overdue']) {
    await expect(page.getByTestId(testId)).toBeVisible()
  }
  await expect(page.locator(bodyRow).first()).toBeVisible()

  // 只看逾期：每行逾期天数都应为正数
  await page.getByTestId('filter-overdue').click()
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(8)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => /^[1-9]\d*\s*天$/.test(text.trim()))
    })
    .toBe(true)
})

test('应收账龄：结算方式与截止日期过滤生效', async ({ page }) => {
  await gotoMenu(page, '应收账龄')
  await expect(page.locator(bodyRow).first()).toBeVisible()

  // 结算方式 = 月结30天
  await page.getByTestId('filter-settlement').click()
  await page.locator('.el-select-dropdown__item:visible').filter({ hasText: '月结30天' }).first().click()
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(7)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === '月结30天')
    })
    .toBe(true)

  // 截止日期设到很久以前：不应再有逾期行（下单日期都晚于该日期）
  await page.getByTestId('btn-reset').click()
  const asOf = page.getByTestId('filter-as-of').locator('input').first()
  await asOf.fill('2000-01-01')
  await asOf.press('Enter')
  await page.keyboard.press('Escape')
  await page.getByTestId('btn-search').click()
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(8)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === '0 天')
    })
    .toBe(true)
})
