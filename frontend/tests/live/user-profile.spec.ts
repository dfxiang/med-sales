import { Buffer } from 'node:buffer'

import { expect, test } from '@playwright/test'

import { gotoMenu, login } from '../e2e/helpers'

/**
 * 运行环境回归：用户资料 / 头像 / 密码自助能力。
 *
 * 覆盖点（对应 docs/用户资料扩展设计.md）：
 * 1) 用户管理页展示显示名称 / 电话 / 邮箱，建号时显示名称默认取用户名；
 * 2) 管理员「重置密码」入口：单字段、无二次确认，重置后旧密码失效；
 * 3) 右上角「个人资料」：显示名称 / 电话 / 邮箱可自助维护，顶栏同步；
 * 4) 头像：上传后顶栏立即更新、匿名接口可读且服务端已规范化为 256×256，可恢复默认；
 * 5) 自助改密：原密码 + 两次确认校验，成功后新旧密码切换（用临时账号）。
 *
 * 所有用例结束都会恢复 / 清理数据，避免污染运行环境。
 */

/** 2×2 的合法 PNG（服务端会统一规范化为 256×256） */
const TINY_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGM8oaHBwMDAxMDAwMDAAAAN6gEcJJUQNAAAAABJRU5ErkJggg=='

function pngSize(buffer: Buffer): { width: number; height: number } {
  // PNG 的 IHDR：宽度/高度分别位于第 16、20 字节（大端）
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) }
}

async function adminHeaders(page: import('@playwright/test').Page) {
  const token = await page.evaluate(() => localStorage.getItem('access_token') || '')
  return { Authorization: `Bearer ${token}` }
}

async function findUserIdByKeyword(
  page: import('@playwright/test').Page,
  headers: Record<string, string>,
  keyword: string,
): Promise<number> {
  const resp = await page.request.get(`/api/users?keyword=${encodeURIComponent(keyword)}`, {
    headers,
  })
  expect(resp.status()).toBe(200)
  const items = (await resp.json()).items as { id: number; username: string }[]
  const hit = items.find((item) => item.username === keyword)
  if (!hit) throw new Error(`未找到用户 ${keyword}`)
  return hit.id
}

test('用户管理：展示资料列，建号默认显示名称，管理员可重置密码', async ({ page }) => {
  await login(page)
  const headers = await adminHeaders(page)
  const username = `live_profile_${Date.now().toString().slice(-8)}`

  await gotoMenu(page, '用户管理')
  const heads = await page.locator('thead th').allInnerTexts()
  expect(heads).toEqual(expect.arrayContaining(['显示名称', '电话', '邮箱']))

  const dialog = page.locator('.el-dialog').filter({ visible: true })
  await page.getByTestId('btn-create').click()
  await page.getByTestId('field-username').fill(username)
  // 显示名称默认跟随用户名
  await expect(page.getByTestId('field-display-name')).toHaveValue(username)
  await page.getByTestId('field-password').fill('pass1234')
  await page.getByTestId('field-phone').fill('13800002222')
  await page.getByTestId('field-email').fill('live@example.com')
  await page.getByTestId('btn-save').click()
  await expect(dialog).toBeHidden()

  const userId = await findUserIdByKeyword(page, headers, username)
  try {
    const row = page.locator('tbody tr').filter({ hasText: username }).first()
    await expect(row).toBeVisible()
    await expect(row).toContainText('13800002222')
    await expect(row).toContainText('live@example.com')

    // 管理员重置密码：只有一个新密码输入框（无原密码、无确认框）
    await row.getByRole('button', { name: '重置密码' }).click()
    const resetDialog = page.getByTestId('reset-password-dialog')
    await expect(resetDialog).toBeVisible()
    await expect(resetDialog.locator('input')).toHaveCount(2)
    await resetDialog.getByTestId('reset-password-new').fill('resetpass123')
    const [resetResponse] = await Promise.all([
      page.waitForResponse((resp) => resp.url().includes('/reset-password')),
      resetDialog.getByTestId('reset-password-save').click(),
    ])
    expect(resetResponse.status()).toBe(200)
    await expect(resetDialog).toBeHidden()

    // 旧密码失效、新密码可登录
    expect(
      (await page.request.post('/api/auth/login', { data: { username, password: 'pass1234' } })).status(),
    ).toBe(401)
    expect(
      (
        await page.request.post('/api/auth/login', {
          data: { username, password: 'resetpass123' },
        })
      ).status(),
    ).toBe(200)
  } finally {
    await page.request.delete(`/api/users/${userId}`, { headers })
    await page.getByTestId('search-keyword').fill('')
    await page.getByTestId('btn-search').click()
  }
})

test('右上角个人资料与头像：自助维护后顶栏同步，用例结束复原', async ({ page }) => {
  await login(page)
  const headers = await adminHeaders(page)
  const meResp = await page.request.get('/api/auth/me', { headers })
  const me = await meResp.json()
  const original = {
    display_name: me.display_name as string | null,
    phone: me.phone as string | null,
    email: me.email as string | null,
  }
  const tempName = `看板管理员-${Date.now().toString().slice(-6)}`

  try {
    // 1) 资料：用户名只读，其余可改
    await page.getByTestId('user-name').hover()
    await page.getByTestId('profile-entry').click()
    const dialog = page.getByTestId('profile-dialog')
    await expect(dialog).toBeVisible()
    await expect(dialog.getByTestId('profile-username')).toBeDisabled()
    await dialog.getByTestId('profile-display-name').fill(tempName)
    await dialog.getByTestId('profile-phone').fill('13900008888')
    await dialog.getByTestId('profile-email').fill('live-admin@example.com')
    await dialog.getByTestId('profile-save').click()
    await expect(dialog).toBeHidden()
    await expect(page.getByTestId('user-name')).toHaveText(tempName)
    await page.getByTestId('user-name').hover()
    await expect(page.getByTestId('user-phone')).toContainText('13900008888')
    await page.keyboard.press('Escape')

    // 2) 头像：上传后顶栏地址变化，匿名接口可读且已被规范化为 256×256
    const before = await page.getByTestId('header-avatar').locator('img').getAttribute('src')
    expect(before).toContain('default.png')

    await page.getByTestId('user-name').hover()
    await page.getByTestId('profile-entry').click()
    await dialog.getByTestId('avatar-input').setInputFiles({
      name: 'live-avatar.png',
      mimeType: 'image/png',
      buffer: Buffer.from(TINY_PNG_BASE64, 'base64'),
    })
    await expect(page.getByTestId('header-avatar').locator('img')).not.toHaveAttribute(
      'src',
      /default\.png/,
    )
    await expect(page.locator('.el-message--success').first()).toBeVisible()

    const src = (await page.getByTestId('header-avatar').locator('img').getAttribute('src')) || ''
    expect(src).toMatch(/\/api\/avatars\/u[0-9]+-[0-9a-f]{32}\.png$/)
    const anonymous = await page.request.get(src) // 不带任何令牌
    expect(anonymous.status()).toBe(200)
    expect(anonymous.headers()['content-type']).toBe('image/png')
    const stored = Buffer.from(await anonymous.body())
    expect(pngSize(stored)).toEqual({ width: 256, height: 256 })

    // 3) 恢复默认头像
    await dialog.getByTestId('avatar-remove').click()
    await expect(page.getByTestId('header-avatar').locator('img')).toHaveAttribute(
      'src',
      /default\.png/,
    )
    await dialog.getByRole('button', { name: '取消' }).click()
  } finally {
    // 复原资料与头像
    await page.request.put('/api/auth/me', { headers, data: original })
    await page.request.delete('/api/auth/me/avatar', { headers })
  }
})

test('自助改密：校验原密码与两次确认，成功后新密码生效（临时账号）', async ({ page }) => {
  await login(page)
  const headers = await adminHeaders(page)
  const username = `live_pw_${Date.now().toString().slice(-8)}`
  const created = await page.request.post('/api/users', {
    headers,
    data: { username, password: 'pass1234' },
  })
  expect(created.status(), await created.text()).toBe(201)
  const userId = (await created.json()).id as number

  try {
    // 用临时账号登录（无角色 → 落在 /403，但顶栏与弹窗可用）
    await page.evaluate(() => localStorage.clear())
    await page.goto('/login')
    await page.getByTestId('username').fill(username)
    await page.getByTestId('password').fill('pass1234')
    await page.getByTestId('login-submit').click()
    await expect(page).toHaveURL(/\/403/, { timeout: 15_000 })

    await page.getByTestId('user-name').hover()
    await page.getByTestId('password-entry').click()
    const dialog = page.getByTestId('password-dialog')
    await expect(dialog).toBeVisible()

    // 两次新密码不一致：前端就地拦截
    await dialog.getByTestId('password-old').fill('pass1234')
    await dialog.getByTestId('password-new').fill('newpass1234')
    await dialog.getByTestId('password-confirm').fill('newpass4321')
    await dialog.getByTestId('password-save').click()
    await expect(page.getByText('两次输入的新密码不一致').first()).toBeVisible()

    // 原密码错误：服务端拒绝
    await dialog.getByTestId('password-old').fill('wrong-old-pass')
    await dialog.getByTestId('password-confirm').fill('newpass1234')
    await dialog.getByTestId('password-save').click()
    await expect(page.getByText('原密码不正确').first()).toBeVisible()

    // 正常改密
    await dialog.getByTestId('password-old').fill('pass1234')
    const [changeResponse] = await Promise.all([
      page.waitForResponse((resp) => resp.url().includes('/auth/me/password')),
      dialog.getByTestId('password-save').click(),
    ])
    expect(changeResponse.status()).toBe(200)
    await expect(dialog).toBeHidden()

    // 旧密码失效、新密码可登录
    expect(
      (await page.request.post('/api/auth/login', { data: { username, password: 'pass1234' } })).status(),
    ).toBe(401)
    expect(
      (
        await page.request.post('/api/auth/login', {
          data: { username, password: 'newpass1234' },
        })
      ).status(),
    ).toBe(200)
  } finally {
    // 用管理员身份清理临时账号
    await page.evaluate(() => localStorage.clear())
    await login(page)
    const adminHeader = await adminHeaders(page)
    await page.request.delete(`/api/users/${userId}`, { headers: adminHeader })
  }
})
