import { expect, test } from '@playwright/test'

import { seed } from './global-setup'
import {
  confirmMessageBox,
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

test('证照管理：新增、编辑、删除', async ({ page }) => {
  const ids = seed()
  const certNo = uniqueCode('LC')
  await gotoMenu(page, '证照管理')
  await page.getByTestId('btn-create').click()
  // 关联对象为远程搜索选择器：先选对象类型，再搜索具体客户
  await fillFormField(page, '对象类型', { type: 'select', value: '客户' })
  await fillFormField(page, '关联对象', { type: 'select', value: 'C00001' })
  await fillFormField(page, '证照类型', { type: 'select', value: '药品经营许可证' })
  await fillFormField(page, '证照编号', certNo)
  await fillFormField(page, '到期日期', { type: 'date', value: '2029-01-01' })
  await submitDialog(page)
  await expectRowVisible(page, certNo)

  // 新建证照默认待审核
  await expect(
    page.locator('tbody tr').filter({ hasText: certNo }).first().locator('td').nth(7),
  ).toContainText('待审核')

  await editRow(page, certNo, '证照编号', certNo)
  await expectRowVisible(page, certNo)
  await deleteRow(page, certNo)
  await expect(page.locator('tbody tr').filter({ hasText: certNo })).toHaveCount(0)
  void ids
})

test('批次管理：新增、编辑、删除', async ({ page }) => {
  const batchNo = uniqueCode('B')
  await gotoMenu(page, '批次管理')
  await page.getByTestId('btn-create').click()
  await fillFormField(page, '商品', { type: 'select', value: '测试药品' })
  await fillFormField(page, '批号', batchNo)
  await fillFormField(page, '生产日期', { type: 'date', value: '2026-01-01' })
  await fillFormField(page, '有效期至', { type: 'date', value: '2028-01-01' })
  await fillFormField(page, '数量', 500)
  await submitDialog(page)
  await expectRowVisible(page, batchNo)

  await editRow(page, batchNo, '数量', 300)
  await deleteRow(page, batchNo)
})

test('GSP 闭环：建档 → 审核 → 归档 → 预警 → 清理', async ({ page }) => {
  const ids = seed()
  const certNo = uniqueCode('CL')

  // 1. 资质档案：初始未建档
  await page.goto(`/gsp/qualification?entity_type=customer&entity_id=${ids.custId}`)
  await expect(page.getByTestId('qual-status')).toContainText('尚未建档')

  // 2. 建档：录入一张未来到期的证照
  await page.getByTestId('qual-add-cert').click()
  await fillFormField(page, '证照类型', { type: 'select', value: '药品经营许可证' })
  await fillFormField(page, '证照编号', certNo)
  await fillFormField(page, '到期日期', { type: 'date', value: '2032-12-31' })
  await page
    .locator('.el-dialog')
    .filter({ visible: true })
    .first()
    .getByTestId('qual-create-save')
    .click()
  await expect(page.locator('.el-message--success').first()).toBeVisible()

  // 待审核资料会阻断交易
  await expect(page.getByTestId('qual-status')).toContainText('交易已被阻断')
  await expect(page.getByTestId('qual-table')).toContainText('待审核')

  // 3. 审核通过 → 资质合规
  await page.locator('tbody tr').filter({ hasText: certNo }).first().getByTestId('qual-approve').click()
  await confirmMessageBox(page, '通过')
  await expect(page.getByTestId('qual-status')).toContainText('资质合规，允许交易')
  await expect(page.locator('tbody tr').filter({ hasText: certNo }).first()).toContainText('有效')

  // 4. 扫描件归档：上传后成为当前版本
  await page.locator('tbody tr').filter({ hasText: certNo }).first().getByTestId('qual-files').click()
  await page.locator('.el-drawer input[type="file"]').setInputFiles({
    name: '药品经营许可证.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 e2e certificate'),
  })
  await expect(page.getByTestId('attachment-table')).toContainText('药品经营许可证.pdf')
  await expect(page.getByTestId('attachment-table')).toContainText('v1 当前')

  // 4.1 PDF 在线预览：接口以 inline 回传，浏览器内置阅读器渲染
  const previewDialog = page
    .locator('.el-dialog')
    .filter({ has: page.getByTestId('attachment-preview') })
  await page.getByTestId('btn-preview').first().click()
  await expect(previewDialog.getByTestId('preview-pdf')).toBeVisible()
  await previewDialog.getByTestId('preview-close').click()
  await expect(previewDialog).toBeHidden()

  // 4.2 图片预览 + 换证留档
  await page.locator('.el-drawer input[type="file"]').setInputFiles({
    name: '营业执照.png',
    mimeType: 'image/png',
    buffer: Buffer.from('\x89PNG\r\n\x1a\n e2e image'),
  })
  await expect(page.getByTestId('attachment-table')).toContainText('营业执照.png')
  await expect(page.getByTestId('attachment-table')).toContainText('v2 当前')
  await page.getByTestId('btn-preview').first().click()
  await expect(previewDialog.getByTestId('preview-image')).toBeVisible()
  await previewDialog.getByTestId('preview-close').click()

  // 打开「显示历史版本」后 PDF 仍在（v1 历史）
  await page.locator('.el-drawer').getByTestId('chk-history').click()
  await expect(page.getByTestId('attachment-table')).toContainText('v1 历史')
  await page.keyboard.press('Escape')

  // 5. 预警中心：统计卡片与列表可用
  await gotoMenu(page, '预警中心')
  await expect(page.getByTestId('gsp-alerts')).toBeVisible()
  await expect(page.getByTestId('alert-stat-expired')).toBeVisible()
  await expect(page.getByTestId('alert-table')).toBeVisible()

  // 6. 清理：删除测试证照，避免影响后续销售/采购用例
  await gotoMenu(page, '证照管理')
  await expectRowVisible(page, certNo)
  await deleteRow(page, certNo)
})
