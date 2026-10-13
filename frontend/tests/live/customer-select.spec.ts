import { expect, test } from '@playwright/test'

import { login } from '../e2e/helpers'

/**
 * 客户选择控件（components/CustomerSelect.vue）在运行环境的回归：
 * 输入名称片段要能立刻匹配到候选并据此过滤列表。
 *
 * 曾经的问题：页面预拉全量数据导致下拉候选项为空/极慢，输入名称点「查询」也没有反应，
 * 所以这里用 5s 的短超时专门守护「候选要马上出现」。
 */
const bodyRow = '.el-table__body-wrapper tbody tr'

test.beforeEach(async ({ page }) => {
  await login(page)
})

/** 打开客户下拉、按名称片段搜索、选中第一行那家客户，返回客户名称。 */
async function pickFirstRowCustomer(
  page: import('@playwright/test').Page,
  url: string,
  customerColumnIndex: number,
) {
  await page.goto(url)
  const firstRow = page.locator(bodyRow).first()
  await expect(firstRow).toBeVisible()
  const customerName = (await firstRow.locator('td').nth(customerColumnIndex).innerText()).trim()

  const select = page.getByTestId('filter-customer')
  await select.click()
  await select.locator('input').fill(customerName.slice(0, 2))
  const option = page
    .locator('.el-select-dropdown__item:visible')
    .filter({ hasText: customerName })
    .first()
  await expect(option).toBeVisible({ timeout: 5_000 })
  await option.click()
  await page.keyboard.press('Escape')
  return customerName
}

test('销售订单：客户下拉按名称模糊匹配，筛选后列表只剩该客户', async ({ page }) => {
  const customerName = await pickFirstRowCustomer(page, '/sales/orders', 1)
  await page.getByTestId('btn-search').click()
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(2)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === customerName)
    })
    .toBe(true)
})

test('收款记录：客户下拉选中即过滤（订单号列显示业务单号）', async ({ page }) => {
  const customerName = await pickFirstRowCustomer(page, '/finance/payments', 1)
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(2)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === customerName)
    })
    .toBe(true)
  await expect(page.locator(bodyRow).first().locator('td').first()).toHaveText(/^SO\d+$/)
})

test('应收账龄：客户下拉选中即过滤', async ({ page }) => {
  const customerName = await pickFirstRowCustomer(page, '/finance/receivables', 0)
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(1)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === customerName)
    })
    .toBe(true)
})

test('客户汇总：客户下拉过滤只剩该客户', async ({ page }) => {
  const customerName = await pickFirstRowCustomer(page, '/reports/customers', 1)
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(2)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === customerName)
    })
    .toBe(true)
})

test('退货管理：展示原订单号与客户名称，且可按客户过滤', async ({ page }) => {
  await page.goto('/returns')
  const firstRow = page.locator(bodyRow).first()
  await expect(firstRow).toBeVisible()
  const orderNo = (await firstRow.locator('td').nth(1).innerText()).trim()
  const customerName = (await firstRow.locator('td').nth(2).innerText()).trim()
  expect(orderNo).toMatch(/^SO\d+$/)
  expect(customerName).not.toMatch(/^\d+$/)

  const select = page.getByTestId('filter-customer')
  await select.click()
  await select.locator('input').fill(customerName.slice(0, 2))
  const option = page
    .locator('.el-select-dropdown__item:visible')
    .filter({ hasText: customerName })
    .first()
  await expect(option).toBeVisible({ timeout: 5_000 })
  await option.click()
  await page.keyboard.press('Escape')
  await page.getByTestId('btn-search').click()
  await expect
    .poll(async () => {
      const cells = await page.locator(`${bodyRow} td:nth-child(3)`).allInnerTexts()
      return cells.length > 0 && cells.every((text) => text.trim() === customerName)
    })
    .toBe(true)
})
