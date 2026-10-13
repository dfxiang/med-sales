import { expect, test } from '@playwright/test'

test('未登录访问受保护页面会跳转登录页', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login/)
})

test('登录失败提示错误', async ({ page }) => {
  await page.goto('/login')
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('wrong-password')
  await page.getByTestId('login-submit').click()
  await expect(page.getByText('用户名或密码错误')).toBeVisible()
})

test('登录成功后进入看板并展示经营数据', async ({ page }) => {
  await page.goto('/login')
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByTestId('login-submit').click()

  await expect(page).toHaveURL(/\/dashboard/)
  await expect(page.getByTestId('dashboard')).toBeVisible()
  await expect(page.getByText('今日销售额')).toBeVisible()
  await expect(page.getByTestId('user-name')).toHaveText('admin')
})

test('退出登录后回到登录页', async ({ page }) => {
  await page.goto('/login')
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/dashboard/)

  await page.getByTestId('user-name').hover()
  await page.getByTestId('logout').click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page).toHaveURL(/\/login/)
})

test('右上角个人资料：保存后顶栏显示名称同步更新', async ({ page }) => {
  await page.goto('/login')
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/dashboard/)

  await page.getByTestId('user-name').hover()
  await page.getByTestId('profile-entry').click()
  const dialog = page.getByTestId('profile-dialog')
  await expect(dialog).toBeVisible()
  // 用户名只读，其余资料可改
  await expect(dialog.getByTestId('profile-username')).toBeDisabled()

  await dialog.getByTestId('profile-display-name').fill('系统管理员')
  await dialog.getByTestId('profile-phone').fill('13900001111')
  await dialog.getByTestId('profile-email').fill('admin@example.com')
  await dialog.getByTestId('profile-save').click()
  await expect(dialog).toBeHidden()

  await expect(page.getByTestId('user-name')).toHaveText('系统管理员')
  await page.getByTestId('user-name').hover()
  await expect(page.getByTestId('user-email')).toContainText('admin@example.com')

  // 复原，避免影响其它用例（显示名称回填值即用户名 admin）
  await page.getByTestId('profile-entry').click()
  await dialog.getByTestId('profile-display-name').fill('admin')
  await dialog.getByTestId('profile-phone').fill('')
  await dialog.getByTestId('profile-email').fill('')
  await dialog.getByTestId('profile-save').click()
  await expect(dialog).toBeHidden()
  await expect(page.getByTestId('user-name')).toHaveText('admin')
})

test('右上角修改密码：校验两次新密码与原密码', async ({ page }) => {
  await page.goto('/login')
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/dashboard/)

  await page.getByTestId('user-name').hover()
  await page.getByTestId('password-entry').click()
  const dialog = page.getByTestId('password-dialog')
  await expect(dialog).toBeVisible()

  // 两次新密码不一致：前端就地拦截
  await dialog.getByTestId('password-old').fill('admin123')
  await dialog.getByTestId('password-new').fill('newpass1234')
  await dialog.getByTestId('password-confirm').fill('newpass4321')
  await dialog.getByTestId('password-save').click()
  await expect(page.getByText('两次输入的新密码不一致').first()).toBeVisible()

  // 原密码错误：服务端拒绝
  await dialog.getByTestId('password-old').fill('wrong-old-pass')
  await dialog.getByTestId('password-confirm').fill('newpass1234')
  await dialog.getByTestId('password-save').click()
  await expect(page.getByText('原密码不正确').first()).toBeVisible()

  // 只读校验，不做真实改密（真实往返在 live 用例中用临时账号覆盖）
  await dialog.getByRole('button', { name: '取消' }).click()
})
