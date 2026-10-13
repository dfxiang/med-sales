import { expect, test } from '@playwright/test'

import {
  deleteRow,
  editRow,
  expectRowHidden,
  expectRowVisible,
  fillFormField,
  gotoMenu,
  login,
  submitDialog,
  uniqueCode,
} from './helpers'

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('客户管理：新增、编辑、删除', async ({ page }) => {
  const code = uniqueCode('C')
  await gotoMenu(page, '客户管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户编码', code)
  await fillFormField(page, '客户名称', 'E2E测试医院')
  await fillFormField(page, '客户类型', { type: 'select', value: '三级医院' })
  await fillFormField(page, '信用额度', 500000)
  await submitDialog(page)
  await expectRowVisible(page, code)

  await editRow(page, code, '客户名称', 'E2E测试医院-改')
  await expectRowVisible(page, 'E2E测试医院-改')

  await deleteRow(page, 'E2E测试医院-改')
  await expectRowHidden(page, code)
})

test('客户管理：新增后客户选择控件立刻可选（共享候选缓存会失效）', async ({ page }) => {
  const code = uniqueCode('C')
  const name = `E2E缓存医院${code.slice(-4)}`
  await gotoMenu(page, '客户管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '客户编码', code)
  await fillFormField(page, '客户名称', name)
  await submitDialog(page)
  await expectRowVisible(page, code)

  // 销售订单页的客户下拉用的是全站共享候选缓存，新增客户后必须能看到
  await gotoMenu(page, '销售订单')
  const select = page.getByTestId('filter-customer')
  await select.click()
  await select.locator('input').fill(name)
  await expect(
    page.locator('.el-select-dropdown__item:visible').filter({ hasText: name }).first(),
  ).toBeVisible({ timeout: 5_000 })
  await page.keyboard.press('Escape')

  await gotoMenu(page, '客户管理')
  await deleteRow(page, code)
  await expectRowHidden(page, code)
})

test('供应商管理：新增、编辑、删除', async ({ page }) => {
  const code = uniqueCode('S')
  await gotoMenu(page, '供应商管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '编码', code)
  await fillFormField(page, '供应商名称', 'E2E测试供应商')
  await fillFormField(page, '账期天数', 45)
  await submitDialog(page)
  await expectRowVisible(page, code)

  await editRow(page, code, '供应商名称', 'E2E测试供应商-改')
  await expectRowVisible(page, 'E2E测试供应商-改')

  await deleteRow(page, 'E2E测试供应商-改')
  await expectRowHidden(page, code)
})

test('仓库管理：新增、编辑、删除', async ({ page }) => {
  const code = uniqueCode('WH')
  await gotoMenu(page, '仓库管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '仓库编码', code)
  await fillFormField(page, '仓库名称', 'E2E测试仓')
  await submitDialog(page)
  await expectRowVisible(page, code)

  await editRow(page, code, '仓库名称', 'E2E测试仓-改')
  await expectRowVisible(page, 'E2E测试仓-改')

  await deleteRow(page, 'E2E测试仓-改')
  await expectRowHidden(page, code)
})
