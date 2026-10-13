import { expect, test } from '@playwright/test'

import { login } from '../e2e/helpers'

/**
 * 候选数据接口（`/api/options/*`）的运行环境回归。
 *
 * 背景：报表页按一个权限开放（如 `report:view`），但页面里的筛选控件需要候选数据。
 * 修复前下拉直接调管理页列表接口（`/employees` 需要 `org:employee:view`），于是
 * 「右侧有数据、却弹出权限不足」。现在候选数据走独立接口：登录即可访问，且
 * **只返回 id / 编码 / 名称**，管理页接口（商品成本价、客户联系方式等）的权限模型不变。
 */

test('受限角色：报表筛选控件可用，且不触发「权限不足」', async ({ page }) => {
  await login(page)
  const adminToken = await page.evaluate(() => localStorage.getItem('access_token') || '')
  const adminHeaders = { Authorization: `Bearer ${adminToken}` }
  const stamp = Date.now().toString().slice(-8)
  const username = `perm_filter_${stamp}`
  const roleName = `仅看板报表-${stamp}`

  const permissionIds: number[] = []
  for (const code of ['dashboard:view', 'report:view']) {
    const resp = await page.request.get(`/api/permissions?keyword=${code}`, { headers: adminHeaders })
    const items = (await resp.json()).items as { id: number; code: string }[]
    const hit = items.find((item) => item.code === code)
    expect(hit, `未找到权限 ${code}`).toBeTruthy()
    permissionIds.push(hit!.id)
  }

  const createdUser = await page.request.post('/api/users', {
    headers: adminHeaders,
    data: { username, password: 'filter1234', display_name: '报表只读账号' },
  })
  expect(createdUser.status(), await createdUser.text()).toBe(201)
  const userId = (await createdUser.json()).id as number

  const createdRole = await page.request.post('/api/roles', {
    headers: adminHeaders,
    data: { name: roleName, description: 'live 回归：仅看板与报表权限' },
  })
  expect(createdRole.status(), await createdRole.text()).toBe(201)
  const roleId = (await createdRole.json()).id as number
  await page.request.post(`/api/roles/${roleId}/permissions`, {
    headers: adminHeaders,
    data: { permission_ids: permissionIds },
  })
  await page.request.post(`/api/users/${userId}/roles`, {
    headers: adminHeaders,
    data: { role_ids: [roleId] },
  })

  const forbidden: string[] = []
  page.on('response', (response) => {
    if (response.status() === 403) forbidden.push(response.url())
  })

  try {
    await page.evaluate(() => localStorage.clear())
    await page.goto('/login')
    await page.getByTestId('username').fill(username)
    await page.getByTestId('password').fill('filter1234')
    await page.getByTestId('login-submit').click()
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 })

    await page.locator('.el-menu-item').getByText('销售员业绩', { exact: true }).click()

    // 1) 报表数据本身可看（这是修复前就正常的部分）
    await expect(page.locator('tbody tr').first()).toBeVisible()
    await expect(page.locator('.el-pagination__total')).toContainText('共')

    // 2) 筛选控件可用（候选来自登录即可访问的候选接口），不再弹出权限不足
    const filters = page.locator('.page-toolbar .el-select')
    await expect(filters.nth(0)).toContainText('请输入工号/姓名')
    await filters.nth(0).click()
    await expect(page.locator('.el-select-dropdown__item:visible').first()).toBeVisible()
    await page.keyboard.press('Escape')

    // 3) 全程没有 403，也没有「权限不足」提示
    expect(forbidden, forbidden.join('\n')).toHaveLength(0)
    await expect(page.locator('.el-message--error')).toHaveCount(0)
  } finally {
    await page.evaluate(() => localStorage.clear())
    await page.request.delete(`/api/users/${userId}`, { headers: adminHeaders })
    await page.request.delete(`/api/roles/${roleId}`, { headers: adminHeaders })
  }
})

test('候选接口只返回 id / 编码 / 名称，不带成本价等业务字段', async ({ page }) => {
  await login(page)
  const token = await page.evaluate(() => localStorage.getItem('access_token') || '')
  const headers = { Authorization: `Bearer ${token}` }

  const product = await page.request.get('/api/options/product', { headers })
  expect(product.status()).toBe(200)
  const items = (await product.json()) as Record<string, unknown>[]
  expect(items.length).toBeGreaterThan(0)
  expect(Object.keys(items[0]).sort()).toEqual(['code', 'id', 'name'])
  expect(JSON.stringify(items)).not.toContain('cost_price')

  const customer = await page.request.get('/api/options/customer?keyword=医院', { headers })
  expect(customer.status()).toBe(200)
  const customers = (await customer.json()) as Record<string, unknown>[]
  expect(JSON.stringify(customers)).not.toContain('credit_limit')
  expect(JSON.stringify(customers)).not.toContain('phone')
})

test('管理员：筛选控件照常可用（权限判断不误伤）', async ({ page }) => {
  await login(page)
  await page.locator('.el-menu-item').getByText('销售员业绩', { exact: true }).click()
  const filters = page.locator('.page-toolbar .el-select')
  await expect(filters.nth(0)).toBeEnabled()
  await expect(filters.nth(0)).not.toContainText('权限')
  await filters.nth(0).click()
  await page.locator('.el-select-dropdown__item:visible').first().click()
  await expect(page.locator('tbody tr').first()).toBeVisible()
})
