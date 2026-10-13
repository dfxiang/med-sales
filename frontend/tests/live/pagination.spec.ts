import { expect, test, type Locator, type Page } from '@playwright/test'

import { login } from '../e2e/helpers'

/**
 * 针对运行中环境的列表分页验证：分页控件是否存在、每页条数能否调整、翻页/跳页是否生效。
 * 断言基于页面实时显示的总数，不写死库中数据，便于重复运行。
 */

const pages = [
  { name: '采购订单', path: '/purchase/orders' },
  { name: '销售订单', path: '/sales/orders' },
  { name: '库存查询', path: '/inventory/stock' },
  { name: '库存流水', path: '/inventory/movements' },
  { name: '退货管理', path: '/returns' },
]

function pagerOf(page: Page): Locator {
  return page.locator('.el-pagination').first()
}

async function readTotal(page: Page): Promise<number> {
  const text = (await pagerOf(page).innerText()).replace(/\s+/g, ' ')
  const match = text.match(/共\s*([\d,]+)\s*条/)
  return match ? Number(match[1].replace(/,/g, '')) : 0
}

async function activePage(page: Page): Promise<number> {
  return Number(await pagerOf(page).locator('.el-pager li.is-active').innerText())
}

async function setPageSize(page: Page, value: number): Promise<void> {
  await pagerOf(page).locator('.el-pagination__sizes .el-select').click()
  await page
    .locator('.el-select-dropdown__item:visible')
    .filter({ hasText: String(value) })
    .first()
    .click()
}

test.beforeEach(async ({ page }) => {
  await login(page)
})

for (const target of pages) {
  test(`${target.name}：分页存在且每页条数可调整`, async ({ page }) => {
    await page.goto(target.path)
    await expect(page.locator('.el-table__row').first()).toBeVisible()

    const pager = pagerOf(page)
    await expect(pager).toBeVisible()

    const total = await readTotal(page)
    expect(total, '列表应有不少于 20 条数据才能验证翻页').toBeGreaterThan(20)

    // 1) 存在「每页条数」选择器
    await expect(pager.locator('.el-pagination__sizes')).toBeVisible()

    // 2) 每页条数可调整：50 / 10 / 20，行数与选择一致且回到第 1 页
    for (const size of [50, 10, 20]) {
      await setPageSize(page, size)
      await expect(page.locator('.el-table__row')).toHaveCount(Math.min(size, total))
      await expect.poll(() => activePage(page)).toBe(1)
    }

    // 3) 下一页 / 上一页
    const firstRowPage1 = await page.locator('.el-table__row').first().innerText()
    await pager.locator('.btn-next').click()
    await expect.poll(() => activePage(page)).toBe(2)
    await expect
      .poll(async () => page.locator('.el-table__row').first().innerText())
      .not.toBe(firstRowPage1)

    await pager.locator('.btn-prev').click()
    await expect.poll(() => activePage(page)).toBe(1)
    await expect
      .poll(async () => page.locator('.el-table__row').first().innerText())
      .toBe(firstRowPage1)

    // 4) 第 1 页「上一页」禁用
    await expect(pager.locator('.btn-prev')).toBeDisabled()

    // 5) 页码跳转到第 3 页
    const firstRowBeforeJump = await page.locator('.el-table__row').first().innerText()
    await pager.locator('.el-pager li').filter({ hasText: /^3$/ }).first().click()
    await expect.poll(() => activePage(page)).toBe(3)
    await expect
      .poll(async () => page.locator('.el-table__row').first().innerText())
      .not.toBe(firstRowBeforeJump)

    // 6) 查询后回到第 1 页
    await page.locator('[data-test=btn-search]').click()
    await expect.poll(() => activePage(page)).toBe(1)
  })
}
