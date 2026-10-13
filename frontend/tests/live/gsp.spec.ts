import { expect, test } from '@playwright/test'

import { login } from '../e2e/helpers'

/**
 * 针对运行中部署的 GSP 页面验证。
 * 除个别用例会临时创建数据并在结束时清理外，其余用例只读。
 */

test.beforeEach(async ({ page }) => {
  await login(page)
})

test('预警中心：统计卡片、列表与左对齐分页', async ({ page }) => {
  await page.goto('/gsp/alerts')
  await expect(page.getByTestId('gsp-alerts')).toBeVisible()
  for (const key of ['expired', 'within_30', 'within_60', 'within_90', 'pending_review']) {
    await expect(page.getByTestId(`alert-stat-${key}`)).toBeVisible()
  }
  const pager = page.locator('.el-pagination').first()
  await expect(pager).toBeVisible()
  await expect(pager.locator('.el-pagination__sizes')).toBeVisible()
  const align = await pager.evaluate((el) => getComputedStyle(el).justifyContent)
  expect(align).toBe('flex-start')

  // 按类别筛选后回到第 1 页
  await page.getByTestId('alert-category').click()
  await page.locator('.el-select-dropdown__item:visible').filter({ hasText: '证照' }).first().click()
  await expect(page.getByTestId('alert-table')).toBeVisible()
})

test('资质档案：按主体查看一户一档', async ({ page }) => {
  // 从客户列表进入资质档案
  await page.goto('/customers')
  const row = page.locator('tbody tr').first()
  await expect(row).toBeVisible()
  await row.getByTestId('btn-qualification').click()
  await expect(page).toHaveURL(/\/gsp\/qualification/)
  await expect(page.getByTestId('qual-status')).toBeVisible()
  await expect(page.getByTestId('qual-table')).toBeVisible()
  const pager = page.locator('.el-pagination').first()
  await expect(pager).toBeVisible()
  expect(await pager.evaluate((el) => getComputedStyle(el).justifyContent)).toBe('flex-start')
})

test('证照管理：关联对象为可搜索选择器、含审核与扫描件入口', async ({ page, request }) => {
  // 台账可能为空（全新库没有任何证照），这里临时建一条用于验证行内操作入口，结束时删除。
  const loginResp = await request.post('/api/auth/login', {
    data: { username: 'admin', password: 'admin123' },
  })
  expect(loginResp.ok()).toBeTruthy()
  const headers = { Authorization: `Bearer ${(await loginResp.json()).access_token}` }
  const created = await request.post('/api/gsp/certificates', {
    headers,
    data: { entity_type: 'customer', entity_id: 2, cert_type: '营业执照', cert_no: 'UI-ROW-REGRESSION' },
  })
  expect(created.status(), await created.text()).toBe(201)
  const certId = (await created.json()).id

  try {
    await page.goto('/gsp/certificates')
    await expect(page.locator('.el-table__row').first()).toBeVisible()

    await page.getByTestId('btn-create').click()
    const dialog = page.locator('.el-dialog').filter({ visible: true }).first()
    const entityItem = dialog.locator('.el-form-item').filter({ hasText: '关联对象' }).first()
    // 未选择对象类型时，关联对象选择器处于禁用状态
    await expect(entityItem.locator('input')).toBeDisabled()

    const typeItem = dialog.locator('.el-form-item').filter({ hasText: '对象类型' }).first()
    await typeItem.locator('.el-select').click()
    await page.locator('.el-select-dropdown__item:visible').filter({ hasText: '客户' }).first().click()
    // 选完类型后可搜索客户
    await expect(entityItem.locator('input')).toBeEnabled()
    await entityItem.locator('.el-select').click()
    await expect(page.locator('.el-select-dropdown__item:visible').first()).toBeVisible()
    await page.keyboard.press('Escape')
    await dialog.getByRole('button', { name: '取消' }).click()

    // 台账行内含审核/扫描件/档案操作
    const firstRow = page.locator('tbody tr').first()
    await expect(firstRow.getByTestId('btn-attachments')).toBeVisible()
    await expect(firstRow.getByTestId('btn-profile')).toBeVisible()
  } finally {
    await request.delete(`/api/gsp/certificates/${certId}`, { headers })
  }
})

test('看板：GSP 合规预警卡片可跳转预警中心', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page.getByTestId('dashboard-gsp')).toBeVisible()
  await page.getByTestId('dashboard-gsp-more').click()
  await expect(page).toHaveURL(/\/gsp\/alerts/)
  await expect(page.getByTestId('gsp-alerts')).toBeVisible()
})

/**
 * 回归：nginx 默认 client_max_body_size 为 1MB，会让手机拍摄的证照照片（通常 2~5MB）
 * 在网关层被 413 拦截。本用例通过网关上传一张 1.5MB 的图片，确保能到达 API。
 * 会临时创建一条证照，结束时（无论成败）删除。
 */
test('证照扫描件：1.5MB 图片可经网关上传（回归 nginx 1MB 限制）', async ({ request }) => {
  const login = await request.post('/api/auth/login', {
    data: { username: 'admin', password: 'admin123' },
  })
  expect(login.ok()).toBeTruthy()
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` }

  const created = await request.post('/api/gsp/certificates', {
    headers,
    data: { entity_type: 'customer', entity_id: 2, cert_type: '营业执照', cert_no: 'GATEWAY-REGRESSION' },
  })
  expect(created.status()).toBe(201)
  const certId = (await created.json()).id
  try {
    const upload = await request.post(`/api/gsp/certificates/${certId}/attachments`, {
      headers,
      multipart: {
        file: {
          name: 'license.jpg',
          mimeType: 'image/jpeg',
          buffer: Buffer.alloc(1_500_000, 7),
        },
      },
    })
    expect(upload.status(), await upload.text()).toBe(201)
    expect((await upload.json()).size).toBe(1_500_000)

    // 预览：接口以 inline 回传 S3 对象，浏览器可直接渲染
    const attachmentId = (await upload.json()).id
    const preview = await request.get(`/api/gsp/attachments/${attachmentId}/preview`, {
      headers,
    })
    expect(preview.status(), await preview.text()).toBe(200)
    expect(preview.headers()['content-disposition']).toContain('inline')
    expect(preview.headers()['content-type']).toContain('image/jpeg')
  } finally {
    await request.delete(`/api/gsp/certificates/${certId}`, { headers })
  }
})
