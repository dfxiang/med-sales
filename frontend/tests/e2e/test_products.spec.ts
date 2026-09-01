import { expect, test } from '@playwright/test'

import {
  deleteRow,
  editRow,
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

test('商品分类：新增、编辑、删除', async ({ page }) => {
  const code = uniqueCode('CAT')
  await gotoMenu(page, '商品分类')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '分类编码', code)
  await fillFormField(page, '分类名称', 'E2E分类')
  await submitDialog(page)
  await expectRowVisible(page, code)
  await editRow(page, code, '分类名称', 'E2E分类-改')
  await deleteRow(page, 'E2E分类-改')
})

test('生产厂家：新增、编辑、删除', async ({ page }) => {
  const name = uniqueCode('厂家')
  await gotoMenu(page, '生产厂家')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '厂家名称', name)
  await submitDialog(page)
  await expectRowVisible(page, name)
  await editRow(page, name, '国家/地区', '中国')
  await deleteRow(page, name)
})

test('商品管理：新增、编辑、删除', async ({ page }) => {
  const sku = uniqueCode('SKU')
  await gotoMenu(page, '商品管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, 'SKU', sku)
  await fillFormField(page, '商品名称', 'E2E测试商品')
  await fillFormField(page, '分类', { type: 'select', value: '化学药品' })
  await fillFormField(page, '生产厂家', { type: 'select', value: '测试制药' })
  await fillFormField(page, '主要供应商', { type: 'select', value: '测试供应商' })
  await fillFormField(page, '成本价', 20)
  await fillFormField(page, '标准售价', 30)
  await fillFormField(page, '上市日期', { type: 'date', value: '2026-01-01' })
  await submitDialog(page)
  await expectRowVisible(page, sku)

  await editRow(page, sku, '商品名称', 'E2E测试商品-改')
  await expectRowVisible(page, 'E2E测试商品-改')
  await deleteRow(page, 'E2E测试商品-改')
})

test('价格调整：选择商品并调价，历史可见', async ({ page }) => {
  await gotoMenu(page, '价格调整')
  await page.locator('[data-test="product-select"]').click()
  await page.locator('.el-select-dropdown__item:visible').filter({ hasText: 'SKU-E2E-001' }).first().click()
  await expect(page.getByTestId('price-table')).toBeVisible()

  await page.getByTestId('btn-adjust').click()
  await fillFormField(page, '生效日期', { type: 'date', value: '2026-09-01' })
  await fillFormField(page, '新价格', 18)
  await fillFormField(page, '调价原因', 'E2E挂网价调整')
  await submitDialog(page)
  await expect(page.locator('tbody tr').filter({ hasText: '18.00' }).first()).toBeVisible()
})
