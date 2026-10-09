<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'

import CrudPage from '@/components/CrudPage.vue'
import request from '@/utils/request'
import { certificateApi } from '@/api/gsp'
import { statusTagMap } from '@/utils/constants'

const entityTypeOptions = [
  { label: '客户', value: 'customer' },
  { label: '供应商', value: 'supplier' },
  { label: '商品', value: 'product' },
  { label: '生产厂家', value: 'manufacturer' },
]

const certStatusOptions = [
  { label: '有效', value: '有效' },
  { label: '即将到期', value: '即将到期' },
  { label: '过期', value: '过期' },
]

const config = {
  title: '证照管理',
  api: certificateApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'entity_type', label: '对象类型', width: 110 },
    { prop: 'entity_id', label: '对象 ID', width: 90 },
    { prop: 'cert_type', label: '证照类型', width: 160 },
    { prop: 'cert_no', label: '证照编号', width: 180 },
    { prop: 'valid_from', label: '生效日期', type: 'date', width: 120 },
    { prop: 'valid_to', label: '到期日期', type: 'date', width: 120 },
    { prop: 'status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 100 },
  ],
  searchFields: [
    { prop: 'entity_type', label: '对象类型', type: 'select', options: entityTypeOptions },
    { prop: 'status', label: '状态', type: 'select', options: certStatusOptions },
  ],
  formFields: [
    { prop: 'entity_type', label: '对象类型', type: 'select', required: true, options: entityTypeOptions, span: 12 },
    { prop: 'entity_id', label: '对象 ID', type: 'number', required: true, span: 12 },
    { prop: 'cert_type', label: '证照类型', type: 'input', required: true, span: 12 },
    { prop: 'cert_no', label: '证照编号', type: 'input', span: 12 },
    { prop: 'valid_from', label: '生效日期', type: 'date', span: 12 },
    { prop: 'valid_to', label: '到期日期', type: 'date', span: 12 },
    { prop: 'status', label: '状态', type: 'select', default: '有效', options: certStatusOptions, span: 12 },
    { prop: 'remark', label: '备注', type: 'textarea' },
  ],
}

interface Attachment {
  id: number
  certificate_id: number
  file_name: string
  content_type: string | null
  size: number
  uploaded_by: number | null
  created_at: string
}

const filesVisible = ref(false)
const currentCert = ref<Record<string, unknown> | null>(null)
const attachments = ref<Attachment[]>([])
const loadingFiles = ref(false)

async function openFiles(row: Record<string, unknown>) {
  currentCert.value = row
  filesVisible.value = true
  await loadAttachments()
}

async function loadAttachments() {
  if (!currentCert.value) return
  loadingFiles.value = true
  try {
    attachments.value = (await request.get(
      `/gsp/certificates/${currentCert.value.id}/attachments`,
    )) as unknown as Attachment[]
  } finally {
    loadingFiles.value = false
  }
}

async function uploadAttachment(options: UploadRequestOptions) {
  if (!currentCert.value) return
  const form = new FormData()
  form.append('file', options.file)
  try {
    await request.post(`/gsp/certificates/${currentCert.value.id}/attachments`, form)
    ElMessage.success('上传成功')
    options.onSuccess?.(null)
    await loadAttachments()
  } catch (error) {
    options.onError?.(
      error as unknown as Parameters<NonNullable<UploadRequestOptions['onError']>>[0],
    )
  }
}

async function downloadAttachment(attachment: Attachment) {
  const blob = (await request.get(`/gsp/attachments/${attachment.id}/download`, {
    responseType: 'blob',
  })) as unknown as Blob
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = attachment.file_name
  link.click()
  URL.revokeObjectURL(url)
}

async function removeAttachment(attachment: Attachment) {
  await request.delete(`/gsp/attachments/${attachment.id}`)
  ElMessage.success('附件已删除')
  await loadAttachments()
}

function humanSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}
</script>

<template>
  <CrudPage v-bind="config">
    <template #actions="{ row }">
      <el-button link type="primary" data-test="btn-attachments" @click="openFiles(row)">附件</el-button>
    </template>
  </CrudPage>

  <el-drawer v-model="filesVisible" :title="`证照扫描件 · ${currentCert?.cert_type ?? ''}`" size="560px">
    <el-upload
      :show-file-list="false"
      :http-request="uploadAttachment"
      accept=".pdf,.jpg,.jpeg,.png,.webp,.gif,.bmp,.tif,.tiff,.doc,.docx"
    >
      <el-button type="primary" data-test="btn-upload-attachment">上传扫描件</el-button>
    </el-upload>
    <span class="upload-hint">支持 PDF / 图片 / Word，单文件不超过 20MB</span>
    <el-table v-loading="loadingFiles" :data="attachments" border class="mt12" data-test="attachment-table">
      <el-table-column prop="file_name" label="文件名" min-width="180" />
      <el-table-column label="大小" width="100">
        <template #default="{ row }">{{ humanSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="上传时间" width="170">
        <template #default="{ row }">{{ String(row.created_at).replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" data-test="btn-download" @click="downloadAttachment(row)">下载</el-button>
          <el-button link type="danger" data-test="btn-del-attachment" @click="removeAttachment(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loadingFiles && attachments.length === 0" description="暂无扫描件" />
  </el-drawer>
</template>

<style scoped>
.upload-hint {
  margin-left: 12px;
  color: #909399;
  font-size: 12px;
}
.mt12 {
  margin-top: 12px;
}
</style>
