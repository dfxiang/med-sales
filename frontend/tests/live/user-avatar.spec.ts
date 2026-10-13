import { expect, test } from '@playwright/test'

import { login } from '../e2e/helpers'

/**
 * 头像展示的运行环境回归（对应两个已修复缺陷）：
 *
 * 1) 顶栏「有头像却没有图像」：头像是 flex 子项且默认 flex-shrink:1，一旦头像对象
 *    取不到（对象存储里对象丢失 / 上传中断），`el-avatar` 会退化成"灰底 + 首字"，
 *    看着就是没有图像。现在失败时回落到内置默认头像，任何情况下都显示一张图。
 * 2) 个人资料弹窗头像被压扁：头像被右侧操作区（长说明文字）挤压成 55×72 的椭圆。
 *    现在头像设置 `flex: none`，恒为 72×72 正圆。
 */

const TINY_PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGM8oaHBwMDAxMDAwMDAAAAN6gEcJJUQNAAAAABJRU5ErkJggg=='

test('顶栏头像：对象取不到时回落到默认头像，而不是退化成首字', async ({ page }) => {
  await login(page)
  const headers = await adminHeaders(page)

  try {
    // 先给管理员设置一张自定义头像，模拟"用户有头像"
    await page.request.put('/api/auth/me/avatar', {
      headers,
      multipart: {
        file: { name: 'live-avatar.png', mimeType: 'image/png', buffer: Buffer.from(TINY_PNG_BASE64, 'base64') },
      },
    })
    const uploaded = await (await page.request.get('/api/auth/me', { headers })).json()
    const uploadedUrl = uploaded.avatar_url as string
    expect(uploadedUrl).toMatch(/\/api\/avatars\/u[0-9]+-[0-9a-f]{32}\.png$/)

    // 让这张头像的请求返回 404（对象丢失的真实场景）
    await page.route(`**${uploadedUrl}`, (route) =>
      route.fulfill({ status: 404, contentType: 'application/json', body: '{"detail":"头像不存在"}' }),
    )

    await page.reload()
    await page.waitForURL(/dashboard/, { timeout: 20_000 })

    const avatar = page.getByTestId('header-avatar')
    const img = avatar.locator('img')
    await expect(img).toHaveAttribute('src', /\/api\/avatars\/default\.png$/)
    await expect
      .poll(async () => img.evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0))
      .toBe(true)
    await expect(avatar).not.toHaveText(/^[\u4e00-\u9fa5]$/)
  } finally {
    await page.unroute('**/api/avatars/**')
    await page.request.delete('/api/auth/me/avatar', { headers })
    // 清理到「管理员没有自定义头像」即可：套件里其它用例（如 user-profile）默认这个前置状态。
    // 不去还原上传前的具体 URL——万一前置状态本身是上一轮残留的头像，那个对象已经不可达。
    const restored = await (await page.request.get('/api/auth/me', { headers })).json()
    expect(restored.avatar_url).toBe('/api/avatars/default.png')
  }
})

test('个人资料弹窗头像：恒为 72×72 正圆，不被操作区压扁', async ({ page }) => {
  await login(page)
  await page.getByTestId('user-name').hover()
  await page.getByTestId('profile-entry').click()
  const preview = page.getByTestId('avatar-preview')
  await expect(preview).toBeVisible()

  const geometry = await preview.evaluate((el) => {
    const box = el.getBoundingClientRect()
    return {
      width: box.width,
      height: box.height,
      radius: getComputedStyle(el).borderRadius,
      flex: getComputedStyle(el).flex,
    }
  })
  expect(geometry.width).toBeCloseTo(72, 0)
  expect(geometry.height).toBeCloseTo(72, 0)
  expect(geometry.width).toBeCloseTo(geometry.height, 0)
  expect(geometry.radius).toContain('50%')
  expect(geometry.flex.startsWith('0 0')).toBe(true)

  // 头像图确实加载出来了（不是首字兜底）
  await expect
    .poll(async () =>
      preview.locator('img').evaluate((el: HTMLImageElement) => el.complete && el.naturalWidth > 0),
    )
    .toBe(true)
})

async function adminHeaders(page: import('@playwright/test').Page) {
  const token = await page.evaluate(() => localStorage.getItem('access_token') || '')
  return { Authorization: `Bearer ${token}` }
}
