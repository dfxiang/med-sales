import { Page, expect } from '@playwright/test'

export async function login(page: Page) {
  await page.goto('/login')
  await page.getByTestId('username').fill('admin')
  await page.getByTestId('password').fill('admin123')
  await page.getByTestId('login-submit').click()
  await expect(page).toHaveURL(/\/dashboard/)
}

export async function gotoMenu(page: Page, title: string) {
  await page.locator('.el-menu-item').getByText(title, { exact: true }).click()
  await expect(page.locator('.el-card').first()).toBeVisible()
}

export async function fillFormField(
  page: Page,
  label: string,
  value: string | number | { type: 'select' | 'date' | 'switch'; value: string | number | boolean },
) {
  const dialog = page.locator('.el-dialog').filter({ visible: true }).first()
  const item = dialog.locator('.el-form-item').filter({ hasText: label }).first()
  if (typeof value === 'object' && value.type === 'select') {
    await item.locator('.el-select').click()
    const option = page.locator('.el-select-dropdown__item:visible').filter({ hasText: String(value.value) }).first()
    await expect(option).toBeVisible({ timeout: 10_000 })
    await option.click()
    return
  }
  if (typeof value === 'object' && value.type === 'date') {
    const input = item.locator('input').first()
    await input.fill(String(value.value))
    await input.press('Enter')
    return
  }
  if (typeof value === 'object' && value.type === 'switch') {
    const current = await item.locator('.el-switch').getAttribute('class')
    const checked = current?.includes('is-checked') ?? false
    if (Boolean(value.value) !== checked) {
      await item.locator('.el-switch').click()
    }
    return
  }
  await item.locator('input, textarea').first().fill(String(value))
}

export async function submitDialog(page: Page) {
  await page.locator('.el-dialog').filter({ visible: true }).first().getByTestId('btn-save').click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
}

export async function expectRowVisible(page: Page, text: string) {
  await expect(page.locator('tbody tr').filter({ hasText: text }).first()).toBeVisible()
}

export async function expectRowHidden(page: Page, text: string) {
  await expect(page.locator('tbody tr').filter({ hasText: text }).first()).toBeHidden()
}

export async function editRow(page: Page, rowText: string, label: string, value: string) {
  const row = page.locator('tbody tr').filter({ hasText: rowText }).first()
  await row.getByRole('button', { name: '编辑' }).click()
  await fillFormField(page, label, value)
  await submitDialog(page)
}

export async function deleteRow(page: Page, rowText: string) {
  const row = page.locator('tbody tr').filter({ hasText: rowText }).first()
  await row.getByRole('button', { name: '删除' }).click()
  await page.locator('.el-message-box').getByRole('button', { name: '确定' }).click()
  await expect(page.locator('.el-message--success').first()).toBeVisible({ timeout: 15_000 })
}

export function uniqueCode(prefix: string): string {
  return `${prefix}${Date.now().toString().slice(-8)}`
}

export async function pickVisibleOption(page: Page, optionText: string) {
  const option = page.locator('.el-select-dropdown__item:visible').filter({ hasText: optionText }).first()
  await expect(option).toBeVisible({ timeout: 10_000 })
  await option.click()
}

export async function pickItemProduct(page: Page, rowIndex: number, optionText: string) {
  const row = page.locator('.items-table tbody tr').nth(rowIndex)
  await row.locator('.el-select').click()
  await pickVisibleOption(page, optionText)
}

export async function fillItemNumber(page: Page, rowIndex: number, value: string | number) {
  const row = page.locator('.items-table tbody tr').nth(rowIndex)
  await row.locator('.el-input-number input').nth(0).fill(String(value))
}

export async function fillDialogInput(page: Page, label: string, value: string | number) {
  const dialog = page.locator('.el-dialog').filter({ visible: true }).first()
  const item = dialog.locator('.el-form-item').filter({ hasText: label }).first()
  await item.locator('input, textarea').first().fill(String(value))
}

export async function getInventoryQuantity(page: Page): Promise<number> {
  await page.goto('/inventory/stock')
  await expect(page.locator('.el-card').first()).toBeVisible()
  const row = page.locator('tbody tr').filter({ hasText: 'SKU-E2E-001' }).first()
  await expect(row).toBeVisible()
  const cells = row.locator('td')
  const quantity = await cells.nth(3).innerText()
  return Number(quantity.replace(/,/g, ''))
}
