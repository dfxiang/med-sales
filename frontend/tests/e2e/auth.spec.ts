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
