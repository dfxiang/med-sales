import { expect, test, type Page } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 列表页按单号查询（运行环境）：
 * 销售订单列表、采购订单列表都能按单号查（完整单号与片段都命中）——「拿单号找单」是每天的常规操作。
 * 放在 live 套件里守护：源码加了入口但 8088 没重建时，这里会直接失败。
 */
const bodyRow = '.el-table__body-wrapper tbody tr'

test.beforeEach(async ({ page }) => {
  await login(page)
})

/** 等某一列的全部单元格都满足期望（避免读到筛选前的旧数据）。 */
async function expectColumnAll(
  page: Page,
  columnIndex: number,
  match: (text: string) => boolean,
) {
  await expect
    .poll(
      async () => {
        const cells = await page
          .locator(`${bodyRow} td:nth-child(${columnIndex})`)
          .allInnerTexts()
        return cells.length > 0 && cells.every((text) => match(text.trim()))
      },
      { timeout: 30_000 },
    )
    .toBe(true)
}

for (const target of [
  { menu: '销售订单', label: '订单号', pattern: /^SO\d+$/ },
  { menu: '采购订单', label: '采购单号', pattern: /^PO\d+$/ },
]) {
  test(`${target.menu}：按${target.label}查询（完整单号与片段都能命中）`, async ({ page }) => {
    await gotoMenu(page, target.menu)
    await expect(page.locator('thead th').nth(0)).toHaveText(target.label)
    const input = page.getByTestId('filter-order-no')
    await expect(input).toBeVisible()

    const orderNo = (await page.locator(`${bodyRow} td:nth-child(1)`).first().innerText()).trim()
    expect(orderNo).toMatch(target.pattern)

    // 完整单号：只剩这一单
    await input.fill(orderNo)
    await page.getByTestId('btn-search').click()
    await expectColumnAll(page, 1, (text) => text === orderNo)

    // 单号片段（末 6 位）也要命中
    const tail = orderNo.slice(-6)
    await input.fill(tail)
    await page.getByTestId('btn-search').click()
    await expectColumnAll(page, 1, (text) => text.endsWith(tail))
  })
}
