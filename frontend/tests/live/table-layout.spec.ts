import { expect, test } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 表格布局回归：所有列表页单元格单行显示（不换行），超出列宽由省略号 + 悬停提示兜住。
 *
 * 依据 `main.ts` 里 Element Plus 的全局 `table.showOverflowTooltip` 配置；
 * 一旦有人去掉该配置，单元格会恢复默认的 `white-space: normal` 并把行高撑成多行，这里会失败。
 */
const pages = [
  { name: '供应商管理', path: '/suppliers' },
  { name: '商品管理', path: '/products' },
  { name: '客户管理', path: '/customers' },
  { name: '员工管理', path: '/org/employees' },
  { name: '采购订单', path: '/purchase/orders' },
  { name: '销售订单', path: '/sales/orders' },
  { name: '库存查询', path: '/inventory/stock' },
  { name: '库存流水', path: '/inventory/movements' },
  { name: '退货管理', path: '/returns' },
  { name: '收款记录', path: '/finance/payments' },
  { name: '应收账龄', path: '/finance/receivables' },
  { name: '操作日志', path: '/system/logs' },
  { name: '客户汇总', path: '/reports/customers' },
  { name: '商品汇总', path: '/reports/products' },
  { name: '订单明细', path: '/reports/orders' },
]

test.beforeEach(async ({ page }) => {
  await login(page)
})

for (const target of pages) {
  test(`${target.name}：表格单元格不换行`, async ({ page }) => {
    await page.goto(target.path)
    const cells = page.locator('tbody tr').first().locator('td .cell')
    await expect(cells.first()).toBeVisible()

    // 「操作」列里是按钮，故意保留换行（避免按钮被省略号裁掉），不计入断言
    const headers = await page.locator('thead th').allInnerTexts()
    const actionIndex = headers.findIndex((text, index) => text.trim() === '操作' && index === headers.length - 1)
    const whiteSpaces = await cells.evaluateAll((nodes, skipIndex) =>
      nodes
        .map((node, index) => ({ index, ws: getComputedStyle(node as Element).whiteSpace }))
        .filter((item) => item.index !== skipIndex)
        .map((item) => item.ws), actionIndex,
    )
    expect(whiteSpaces.length).toBeGreaterThan(0)
    expect(whiteSpaces.every((value) => value === 'nowrap')).toBeTruthy()
  })
}

test('供应商管理：供应商名称列宽为 330px', async ({ page }) => {
  await gotoMenu(page, '供应商管理')
  const header = page.locator('thead th').nth(2)
  await expect(header).toHaveText('供应商名称')
  const box = await header.boundingBox()
  expect(Math.round(box?.width ?? 0)).toBe(330)
})

test('供应商管理：操作列允许换行，不被省略号裁剪', async ({ page }) => {
  await gotoMenu(page, '供应商管理')
  const actionCell = page.locator('tbody tr').first().locator('td .cell').last()
  await expect(actionCell).toBeVisible()
  const whiteSpace = await actionCell.evaluate((node) => getComputedStyle(node).whiteSpace)
  expect(whiteSpace).toBe('normal')
})
