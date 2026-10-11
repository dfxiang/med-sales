import { expect, test, type Page } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 报表页统一筛选回归（运行环境）：
 * 筛选维度只取「报表行数据自身带得动」的——商品汇总的行是商品、库存状态的行是「仓库 × 商品」，
 * 都只有「商品 / 分类 / 厂家」三个；订单明细的行是订单行，行上本来就有客户，多一个客户筛选。
 * 另外选中后列表真的要过滤（不能只是界面上多了个控件）。
 *
 * 放在 live 套件里守护——这类改动最容易出现「源码已改、8088 仍是旧界面」的假验证。
 */
test.beforeEach(async ({ page }) => {
  await login(page)
})

const bodyRow = '.el-table__body-wrapper tbody tr'
const productFilterIds = ['filter-product', 'filter-category', 'filter-manufacturer']

/** 打开统一控件下拉并选中第一个候选，返回候选文本（形如「编码 - 名称」）。 */
async function pickFirstOption(page: Page, testId: string): Promise<string> {
  const select = page.getByTestId(testId)
  await expect(select).toBeVisible()
  await select.click()
  const option = page.locator('.el-select-dropdown__item:visible').first()
  await expect(option).toBeVisible({ timeout: 20_000 })
  const label = (await option.innerText()).trim()
  await option.click()
  await page.keyboard.press('Escape')
  return label
}

/** 候选文本去掉「编码 - 」前缀，得到表格里展示的名称。 */
function rowTextOf(label: string): string {
  return (label.split(' - ').pop() ?? label).trim()
}

/** 等某一列的全部单元格都等于期望值（避免读到筛选前的旧数据）。 */
async function expectColumnAll(page: Page, columnIndex: number, value: string) {
  await expect
    .poll(
      async () => {
        const cells = await page
          .locator(`${bodyRow} td:nth-child(${columnIndex})`)
          .allInnerTexts()
        return cells.length > 0 && cells.every((text) => text.trim() === value)
      },
      { timeout: 30_000 },
    )
    .toBe(true)
}

test('商品汇总：商品/分类/厂家筛选控件齐全，分类筛选与重置生效', async ({ page }) => {
  await gotoMenu(page, '商品汇总')
  for (const id of productFilterIds) await expect(page.getByTestId(id)).toBeVisible()
  // 报表的行是商品，没有客户维度，不做客户筛选
  await expect(page.getByTestId('filter-customer')).toHaveCount(0)

  const category = rowTextOf(await pickFirstOption(page, 'filter-category'))
  await page.getByTestId('btn-search').click()
  await expectColumnAll(page, 3, category)

  // 重置后不再局限于该分类
  await page.getByTestId('btn-reset').click()
  await expect
    .poll(
      async () => {
        const cells = await page
          .locator(`${bodyRow} td:nth-child(3)`)
          .allInnerTexts()
        return cells.some((text) => text.trim() !== category)
      },
      { timeout: 30_000 },
    )
    .toBe(true)
})

test('订单明细：四个统一筛选控件齐全，商品筛选生效', async ({ page }) => {
  await gotoMenu(page, '订单明细')
  for (const id of [...productFilterIds, 'filter-customer']) {
    await expect(page.getByTestId(id)).toBeVisible()
  }

  const product = rowTextOf(await pickFirstOption(page, 'filter-product'))
  await page.getByTestId('btn-search').click()
  await expectColumnAll(page, 5, product)
})

test('订单明细：按订单号查询（完整单号与片段都能命中）', async ({ page }) => {
  await gotoMenu(page, '订单明细')
  const orderNoInput = page.getByTestId('filter-order-no')
  await expect(orderNoInput).toBeVisible()
  await expect(page.locator('thead th').nth(0)).toHaveText('订单号')

  const orderNo = (await page.locator(`${bodyRow} td:nth-child(1)`).first().innerText()).trim()
  expect(orderNo).toMatch(/^SO\d+$/)

  // 完整单号：只剩该单的明细行
  await orderNoInput.fill(orderNo)
  await page.getByTestId('btn-search').click()
  await expectColumnAll(page, 1, orderNo)

  // 单号片段（末 6 位）也要命中
  const tail = orderNo.slice(-6)
  await page.getByTestId('btn-reset').click()
  await orderNoInput.fill(tail)
  await page.getByTestId('btn-search').click()
  await expect
    .poll(
      async () => {
        const cells = await page
          .locator(`${bodyRow} td:nth-child(1)`)
          .allInnerTexts()
        return cells.length > 0 && cells.every((text) => text.trim().endsWith(tail))
      },
      { timeout: 30_000 },
    )
    .toBe(true)
})

test('库存状态：商品/分类/厂家筛选控件齐全，分类筛选生效', async ({ page }) => {
  await gotoMenu(page, '库存状态')
  for (const id of productFilterIds) await expect(page.getByTestId(id)).toBeVisible()
  // 库存没有客户维度，不做客户筛选
  await expect(page.getByTestId('filter-customer')).toHaveCount(0)

  const category = rowTextOf(await pickFirstOption(page, 'filter-category'))
  await page.getByTestId('btn-search').click()
  await expectColumnAll(page, 4, category)
})

test('销售员业绩：销售员（工号 - 姓名）/ 部门筛选生效，职位不参与筛选', async ({ page }) => {
  await gotoMenu(page, '销售员业绩')
  for (const id of ['filter-employee', 'filter-department']) {
    await expect(page.getByTestId(id)).toBeVisible()
  }
  // 职位只有展示列，筛选栏里不该出现
  await expect(page.locator('.page-toolbar .el-form-item').filter({ hasText: '职位' })).toHaveCount(0)
  await expect(page.locator('thead th').nth(3)).toHaveText('职位')

  // 部门筛选：只剩该部门的销售员
  const department = rowTextOf(await pickFirstOption(page, 'filter-department'))
  await page.getByTestId('btn-search').click()
  await expectColumnAll(page, 3, department)

  // 销售员筛选：取未筛选时的第一名（工号 + 姓名），按工号选中后只剩他
  await page.getByTestId('btn-reset').click()
  const firstRow = page.locator(bodyRow).first()
  await expect(firstRow).toBeVisible()
  const code = (await firstRow.locator('td').nth(0).innerText()).trim()
  const name = (await firstRow.locator('td').nth(1).innerText()).trim()

  const select = page.getByTestId('filter-employee')
  await select.click()
  await select.locator('input').fill(code)
  const option = page.locator('.el-select-dropdown__item:visible').filter({ hasText: code }).first()
  await expect(option).toBeVisible({ timeout: 15_000 })
  await option.click()
  await page.keyboard.press('Escape')
  await page.getByTestId('btn-search').click()
  await expectColumnAll(page, 1, code)
  await expectColumnAll(page, 2, name)
})
