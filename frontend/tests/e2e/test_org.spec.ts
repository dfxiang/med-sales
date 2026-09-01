import { expect, test } from '@playwright/test'

import { seed } from './global-setup'
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

test('部门管理：新增、编辑、删除', async ({ page }) => {
  const code = uniqueCode('D')
  await gotoMenu(page, '部门管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '部门编码', code)
  await fillFormField(page, '部门名称', 'E2E测试部')
  await fillFormField(page, '职责说明', '测试用部门')
  await submitDialog(page)
  await expectRowVisible(page, code)

  await editRow(page, code, '部门名称', 'E2E测试部-改')
  await expectRowVisible(page, 'E2E测试部-改')

  await deleteRow(page, 'E2E测试部-改')
  await expectRowHidden(page, code)
})

test('员工管理：新增、编辑、删除', async ({ page }) => {
  const ids = seed()
  const code = uniqueCode('E')
  await gotoMenu(page, '员工管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '工号', code)
  await fillFormField(page, '姓名', '测试员工')
  await fillFormField(page, '部门 ID', ids.deptId)
  await fillFormField(page, '入职日期', { type: 'date', value: '2026-01-01' })
  await fillFormField(page, '职位', '销售代表')
  await submitDialog(page)
  await expectRowVisible(page, code)

  await editRow(page, code, '职位', '高级销售代表')
  await expectRowVisible(page, '高级销售代表')

  await deleteRow(page, '高级销售代表')
  await expectRowHidden(page, code)
})

test('员工管理：必填校验（缺部门时提示）', async ({ page }) => {
  await gotoMenu(page, '员工管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '工号', uniqueCode('E'))
  await fillFormField(page, '姓名', '无部门员工')
  await page.locator('.el-dialog').filter({ visible: true }).first().getByTestId('btn-save').click()
  await expect(page.locator('.el-message--warning').first()).toBeVisible()
})
