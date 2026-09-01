import { test } from '@playwright/test'

import { seed } from './global-setup'
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

test('证照管理：新增、编辑、删除', async ({ page }) => {
  const ids = seed()
  const certNo = uniqueCode('LC')
  await gotoMenu(page, '证照管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '对象类型', { type: 'select', value: '客户' })
  await fillFormField(page, '对象 ID', ids.custId)
  await fillFormField(page, '证照类型', '药品经营许可证')
  await fillFormField(page, '证照编号', certNo)
  await fillFormField(page, '到期日期', { type: 'date', value: '2029-01-01' })
  await submitDialog(page)
  await expectRowVisible(page, certNo)

  await editRow(page, certNo, '证照类型', '营业执照')
  await expectRowVisible(page, certNo)
  await deleteRow(page, certNo)
})

test('批次管理：新增、编辑、删除', async ({ page }) => {
  const batchNo = uniqueCode('B')
  await gotoMenu(page, '批次管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '商品', { type: 'select', value: '测试药品' })
  await fillFormField(page, '批号', batchNo)
  await fillFormField(page, '生产日期', { type: 'date', value: '2026-01-01' })
  await fillFormField(page, '有效期至', { type: 'date', value: '2028-01-01' })
  await fillFormField(page, '数量', 500)
  await submitDialog(page)
  await expectRowVisible(page, batchNo)

  await editRow(page, batchNo, '数量', 300)
  await deleteRow(page, batchNo)
})
