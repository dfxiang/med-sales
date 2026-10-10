import { expect, test } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 收款记录界面（运行环境回归）：
 * 1) 表格展示业务信息（订单号 / 客户名称），不暴露内部主键；
 * 2) 支持订单号模糊查询与付款日期区间过滤（客户下拉见 customer-select.spec.ts）。
 *
 * 放在 live 套件里守护——这些改动很容易出现「源码已改、8088 仍是旧界面」的假验证。
 */
test.beforeEach(async ({ page }) => {
  await login(page)
})

const bodyRow = '.el-table__body-wrapper tbody tr'

/** 等待列表刷新后，某一列的所有单元格都等于期望值（避免读到筛选前的旧数据）。 */
async function expectColumnAll(
  page: import('@playwright/test').Page,
  columnIndex: number,
  value: string,
) {
  await expect
    .poll(
      async () => {
        const cells = await page
          .locator(`${bodyRow} td:nth-child(${columnIndex})`)
          .allInnerTexts()
        return cells.length > 0 && cells.every((text) => text.trim() === value)
      },
      { timeout: 15_000 },
    )
    .toBe(true)
}

test('收款记录：客户列显示名称，订单号与付款日期筛选可用', async ({ page }) => {
  await gotoMenu(page, '收款记录')

  await expect(page.locator('thead th').nth(0)).toHaveText('订单号')
  await expect(page.locator('thead th').nth(1)).toHaveText('客户')
  await expect(page.getByTestId('filter-customer')).toBeVisible()
  await expect(page.getByTestId('filter-start-date')).toBeVisible()
  await expect(page.getByTestId('filter-end-date')).toBeVisible()
  await expect(page.getByTestId('filter-order-no')).toBeVisible()

  const firstRow = page.locator(bodyRow).first()
  await expect(firstRow).toBeVisible()
  const orderNo = (await firstRow.locator('td').nth(0).innerText()).trim()
  const customerName = (await firstRow.locator('td').nth(1).innerText()).trim()
  const payDate = (await firstRow.locator('td').nth(2).innerText()).trim()
  expect(orderNo).toMatch(/^SO\d+$/)
  expect(customerName).not.toMatch(/^\d+$/)

  // 客户列宽按库内最长客户名称实测（23 字含全角括号，内容需 328px）取 330px，不应被截断
  const customerHeader = page.locator('thead th').nth(1)
  expect(Math.round((await customerHeader.boundingBox())?.width ?? 0)).toBe(330)

  // 订单号模糊查询：只保留该订单
  const orderNoFilter = page.getByTestId('filter-order-no')
  await orderNoFilter.fill(orderNo)
  await page.getByTestId('btn-search').click()
  await expect(page.locator(bodyRow).first()).toBeVisible()
  await expectColumnAll(page, 1, orderNo)

  // 付款日期区间过滤：起止都取该行日期
  await page.getByTestId('btn-reset').click()
  for (const testId of ['filter-start-date', 'filter-end-date']) {
    const input = page.getByTestId(testId).locator('input').first()
    await input.fill(payDate)
    await input.press('Enter')
    await page.keyboard.press('Escape')
  }
  await page.getByTestId('btn-search').click()
  await expect(page.locator(bodyRow).first()).toBeVisible()
  await expectColumnAll(page, 3, payDate)
})
