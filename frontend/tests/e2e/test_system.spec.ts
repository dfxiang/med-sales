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

test('权限管理：新增、编辑、删除', async ({ page }) => {
  const code = uniqueCode('perm')
  await gotoMenu(page, '权限管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '权限编码', code)
  await fillFormField(page, '权限名称', 'E2E权限')
  await submitDialog(page)
  // 内置权限清单有 30+ 条，新建的权限会落在后面的分页里，先用关键词筛出来
  await page.getByTestId('search-keyword').fill(code)
  await page.getByTestId('btn-search').click()
  await expectRowVisible(page, code)
  await editRow(page, code, '权限名称', 'E2E权限-改')
  await deleteRow(page, 'E2E权限-改')
})

test('角色权限：新增角色并分配权限、编辑、删除', async ({ page }) => {
  const roleName = uniqueCode('角色')
  await gotoMenu(page, '角色权限')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '角色名称', roleName)
  await fillFormField(page, '说明', 'E2E测试角色')
  await submitDialog(page)
  await expectRowVisible(page, roleName)

  const row = page.locator('tbody tr').filter({ hasText: roleName }).first()
  await row.getByRole('button', { name: '分配权限' }).click()
  await page.locator('.el-checkbox').filter({ hasText: '全部权限' }).click()
  await page.getByTestId('btn-save-perms').click()
  await expect(page.locator('.el-message--success').first()).toBeVisible()
  await expect(row).toContainText('全部权限')

  await editRow(page, roleName, '角色名称', `${roleName}-改`)
  await expectRowVisible(page, `${roleName}-改`)
  await deleteRow(page, `${roleName}-改`)
})

test('用户管理：新增用户、分配角色、编辑、删除', async ({ page }) => {
  const username = uniqueCode('e2euser')
  await gotoMenu(page, '用户管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '用户名', username)
  await fillFormField(page, '密码', 'pass1234')
  await submitDialog(page)
  await expectRowVisible(page, username)

  const row = page.locator('tbody tr').filter({ hasText: username }).first()
  await row.getByRole('button', { name: '分配角色' }).click()
  await page.locator('.el-checkbox').filter({ hasText: '管理员' }).click()
  await page.getByTestId('btn-save-roles').click()
  await expect(page.locator('.el-message--success').first()).toBeVisible()
  await expect(row).toContainText('管理员')

  await row.getByRole('button', { name: '编辑' }).click()
  await fillFormField(page, '新密码', 'newpass1234')
  await submitDialog(page)
  await row.getByRole('button', { name: '删除' }).click()
  await page.locator('.el-message-box').getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.el-message--success').first()).toBeVisible()
  await expect(row).toBeHidden()
})

test('操作日志：可查询且有记录', async ({ page }) => {
  await gotoMenu(page, '操作日志')
  await expect(page.locator('tbody tr').first()).toBeVisible()
  await page.getByTestId('btn-search').click()
  await expect(page.locator('tbody tr').first()).toBeVisible()
})
