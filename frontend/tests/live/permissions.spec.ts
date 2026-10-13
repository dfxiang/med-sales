import { expect, test } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 针对运行中环境的权限回归：
 * 1) 权限管理页有内置权限目录、模块列与可用的关键词筛选；
 * 2) 角色权限的「分配权限」按模块分组、可搜索；
 * 3) 后端接口级强校验：无角色账号访问受控接口 403，前端落到 /403 页。
 */

test('权限管理：展示内置权限与模块列，关键词可筛选', async ({ page }) => {
  await login(page)
  await gotoMenu(page, '权限管理')

  await expect(page.locator('thead th').nth(2)).toHaveText('模块')
  const rows = page.locator('tbody tr')
  await expect(rows.first()).toBeVisible()
  const totalBefore = await rows.count()
  expect(totalBefore).toBeGreaterThan(1)

  // 内置通配权限在清单中（不可删除）
  await page.getByTestId('search-keyword').fill('all')
  await page.getByTestId('btn-search').click()
  await expect(rows.first()).toContainText('all')
  await expect(rows.first().locator('td').nth(2)).toHaveText('内置')

  // 关键词筛选确实生效（修复前该参数被后端忽略，结果不变）
  const filtered = await rows.count()
  expect(filtered).toBeLessThan(totalBefore)

  await page.getByTestId('search-keyword').fill('sales:manage')
  await page.getByTestId('btn-search').click()
  await expect(rows.first()).toContainText('sales:manage')
  await expect(rows.first().locator('td').nth(2)).toHaveText('销售管理')
})

test('角色权限：分配权限弹窗按模块分组且可搜索', async ({ page }) => {
  await login(page)
  await gotoMenu(page, '角色权限')

  const row = page.locator('tbody tr').filter({ hasText: '管理员' }).first()
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: '分配权限' }).click()

  await expect(page.locator('[data-test="perm-group-system"]')).toBeVisible()
  await expect(page.locator('[data-test="perm-group-sales"]')).toBeVisible()
  await expect(page.getByTestId('perm-system:user:manage')).toBeVisible()

  // 搜索后只保留命中的分组
  await page.getByTestId('perm-search').fill('gsp')
  await expect(page.locator('[data-test="perm-group-gsp"]')).toBeVisible()
  await expect(page.locator('[data-test="perm-group-system"]')).toHaveCount(0)
  await expect(page.getByTestId('perm-gsp:manage')).toBeVisible()

  // 只读检查，不做保存（避免改动运行环境的角色配置）
  await page.locator('.el-dialog').filter({ visible: true }).getByRole('button', { name: '取消' }).click()
})

test('无角色账号：接口 403，前端落 /403 且看不到无权菜单', async ({ page }) => {
  await login(page)
  const adminToken = await page.evaluate(() => localStorage.getItem('access_token') || '')
  const adminHeaders = { Authorization: `Bearer ${adminToken}` }
  const username = `perm_probe_${Date.now().toString().slice(-8)}`

  const created = await page.request.post('/api/users', {
    headers: adminHeaders,
    data: { username, password: 'probe1234', is_active: true },
  })
  expect(created.status(), await created.text()).toBe(201)
  const userId = (await created.json()).id as number

  try {
    // 1) 后端强制校验：无任何角色的账号连用户列表都读不到
    const tokenResp = await page.request.post('/api/auth/login', {
      data: { username, password: 'probe1234' },
    })
    expect(tokenResp.status()).toBe(200)
    const userToken = (await tokenResp.json()).access_token as string
    const denied = await page.request.get('/api/users', {
      headers: { Authorization: `Bearer ${userToken}` },
    })
    expect(denied.status()).toBe(403)
    expect(JSON.stringify(await denied.json())).toContain('权限不足')

    // 2) 前端：登录后落 403，系统管理菜单不可见，直访无权路由仍被拦回 403
    await page.evaluate(() => localStorage.clear())
    await page.goto('/login')
    await page.getByTestId('username').fill(username)
    await page.getByTestId('password').fill('probe1234')
    await page.getByTestId('login-submit').click()

    await expect(page).toHaveURL(/\/403/, { timeout: 15_000 })
    await expect(page.getByTestId('forbidden')).toBeVisible()
    await expect(page.locator('.el-menu-item').filter({ hasText: '用户管理' })).toHaveCount(0)

    await page.goto('/system/users')
    await expect(page).toHaveURL(/\/403/)
    await expect(page.getByTestId('forbidden')).toBeVisible()
  } finally {
    await page.evaluate(() => localStorage.clear())
    await page.request.delete(`/api/users/${userId}`, { headers: adminHeaders })
  }
})

test('权限页面：分页靠左，权限分配弹窗不撑破视口', async ({ page }) => {
  await login(page)
  await gotoMenu(page, '权限管理')

  const pagination = page.locator('.el-pagination').first()
  const table = page.locator('.el-table').first()
  const paginationBox = await pagination.boundingBox()
  const tableBox = await table.boundingBox()
  expect(paginationBox).not.toBeNull()
  expect(tableBox).not.toBeNull()
  // 分页控件靠左：左边缘与表格对齐（AGENTS.md 强制约定）
  expect(Math.abs(paginationBox!.x - tableBox!.x)).toBeLessThan(20)

  await gotoMenu(page, '角色权限')
  const row = page.locator('tbody tr').filter({ hasText: '管理员' }).first()
  await row.getByRole('button', { name: '分配权限' }).click()
  const dialog = page.locator('.el-dialog').filter({ visible: true }).first()
  await expect(dialog).toBeVisible()
  const dialogBox = await dialog.boundingBox()
  const viewport = page.viewportSize()!
  expect(dialogBox!.width).toBeLessThanOrEqual(viewport.width)
  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  )
  expect(horizontalOverflow).toBeLessThanOrEqual(1)
  await dialog.getByRole('button', { name: '取消' }).click()
})

test('只读账号：用户列表可看，维护按钮隐藏且写接口 403', async ({ page }) => {
  await login(page)
  const adminToken = await page.evaluate(() => localStorage.getItem('access_token') || '')
  const adminHeaders = { Authorization: `Bearer ${adminToken}` }
  const stamp = Date.now().toString().slice(-8)
  const username = `perm_viewer_${stamp}`
  const roleName = `只读用户-${stamp}`

  const perms = await page.request.get('/api/permissions?keyword=system:user:view', {
    headers: adminHeaders,
  })
  const viewPermissionId = (await perms.json()).items[0].id as number

  const createdUser = await page.request.post('/api/users', {
    headers: adminHeaders,
    data: { username, password: 'viewer1234', is_active: true },
  })
  expect(createdUser.status(), await createdUser.text()).toBe(201)
  const userId = (await createdUser.json()).id as number

  const createdRole = await page.request.post('/api/roles', {
    headers: adminHeaders,
    data: { name: roleName, description: 'live 回归用只读角色' },
  })
  expect(createdRole.status(), await createdRole.text()).toBe(201)
  const roleId = (await createdRole.json()).id as number
  await page.request.post(`/api/roles/${roleId}/permissions`, {
    headers: adminHeaders,
    data: { permission_ids: [viewPermissionId] },
  })
  await page.request.post(`/api/users/${userId}/roles`, {
    headers: adminHeaders,
    data: { role_ids: [roleId] },
  })

  try {
    // 后端：读放行、写拦截
    const tokenResp = await page.request.post('/api/auth/login', {
      data: { username, password: 'viewer1234' },
    })
    const viewerToken = (await tokenResp.json()).access_token as string
    const viewerHeaders = { Authorization: `Bearer ${viewerToken}` }
    expect((await page.request.get('/api/users', { headers: viewerHeaders })).status()).toBe(200)
    const write = await page.request.post('/api/users', {
      headers: viewerHeaders,
      data: { username: `${username}_x`, password: 'viewer1234' },
    })
    expect(write.status()).toBe(403)

    // 前端：列表可见，但新增/编辑/删除/分配角色按钮全部隐藏；无权菜单不出现
    await page.evaluate(() => localStorage.clear())
    await page.goto('/login')
    await page.getByTestId('username').fill(username)
    await page.getByTestId('password').fill('viewer1234')
    await page.getByTestId('login-submit').click()
    // 该角色没有 dashboard:view，登录后默认跳转被守卫改判到 403
    await expect(page).toHaveURL(/\/403/, { timeout: 15_000 })
    // 菜单只保留有权限的项
    await expect(page.locator('.el-menu-item').filter({ hasText: '用户管理' })).toHaveCount(1)
    await expect(page.locator('.el-menu-item').filter({ hasText: '角色权限' })).toHaveCount(0)

    await page.goto('/system/users')
    await expect(page.locator('tbody tr').first()).toBeVisible()
    await expect(page.getByTestId('btn-create')).toHaveCount(0)
    await expect(page.getByTestId('btn-edit')).toHaveCount(0)
    await expect(page.getByTestId('btn-delete')).toHaveCount(0)
    await expect(page.getByTestId('btn-bind-roles')).toHaveCount(0)
  } finally {
    await page.evaluate(() => localStorage.clear())
    await page.request.delete(`/api/users/${userId}`, { headers: adminHeaders })
    await page.request.delete(`/api/roles/${roleId}`, { headers: adminHeaders })
  }
})
