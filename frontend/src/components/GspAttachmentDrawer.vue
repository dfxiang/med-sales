<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox, type UploadRequestOptions } from 'element-plus'

import { certificateApi, type Certificate, type CertificateAttachment } from '@/api/gsp'
import { humanSize } from '@/utils/gsp'
import GspAttachmentPreview from '@/components/GspAttachmentPreview.vue'

const props = defineProps<{
  modelValue: boolean
  certificate: Certificate | null
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean]; changed: [] }>()

// 与后端 ATTACHMENT_SUFFIXES / ATTACHMENT_MAX_BYTES 保持一致，先在本地拦一道
const ALLOWED_SUFFIXES = [
  '.pdf', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.doc', '.docx',
]
const MAX_BYTES = 20 * 1024 * 1024

const attachments = ref<CertificateAttachment[]>([])
const loading = ref(false)
const includeHistory = ref(false)
const previewVisible = ref(false)
const previewTarget = ref<CertificateAttachment | null>(null)

async function load() {
  if (!props.certificate) return
  loading.value = true
  try {
    attachments.value = (await certificateApi.attachments(
      props.certificate.id,
      includeHistory.value,
    )) as unknown as CertificateAttachment[]
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.certificate?.id],
  ([visible]) => {
    if (visible) {
      includeHistory.value = false
      load()
    }
  },
)

async function upload(options: UploadRequestOptions) {
  if (!props.certificate) return
  const form = new FormData()
  form.append('file', options.file)
  try {
    await certificateApi.uploadAttachment(props.certificate.id, form)
    ElMessage.success('上传成功（新版本生效，旧版本自动留档）')
    options.onSuccess?.(null)
    await load()
    emit('changed')
  } catch (error) {
    options.onError?.(
      error as unknown as Parameters<NonNullable<UploadRequestOptions['onError']>>[0],
    )
  }
}

function beforeUpload(file: File): boolean {
  const name = file.name.toLowerCase()
  if (!ALLOWED_SUFFIXES.some((suffix) => name.endsWith(suffix))) {
    ElMessage.error('仅支持 PDF / 图片 / Word 文件')
    return false
  }
  if (file.size > MAX_BYTES) {
    ElMessage.error(
      `文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB），单文件上限 ${MAX_BYTES / 1024 / 1024}MB`,
    )
    return false
  }
  return true
}

function openPreview(attachment: CertificateAttachment) {
  previewTarget.value = attachment
  previewVisible.value = true
}

async function download(attachment: CertificateAttachment) {
  const blob = (await certificateApi.downloadAttachment(attachment.id)) as unknown as Blob
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = attachment.file_name
  link.click()
  URL.revokeObjectURL(url)
}

async function remove(attachment: CertificateAttachment) {
  await ElMessageBox.confirm(`确定删除「${attachment.file_name}」吗？`, '提示', {
    type: 'warning',
  })
  await certificateApi.removeAttachment(attachment.id)
  ElMessage.success('附件已删除')
  await load()
  emit('changed')
}
</script>

<template>
  <el-drawer
    :model-value="modelValue"
    :title="`证照扫描件 · ${certificate?.cert_type ?? ''}`"
    size="620px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="drawer-toolbar">
      <el-upload
        :show-file-list="false"
        :before-upload="beforeUpload"
        :http-request="upload"
        accept=".pdf,.jpg,.jpeg,.png,.webp,.gif,.bmp,.tif,.tiff,.doc,.docx"
      >
        <el-button type="primary" data-test="btn-upload-attachment">上传扫描件</el-button>
      </el-upload>
      <el-checkbox v-model="includeHistory" data-test="chk-history" @change="load">
        显示历史版本
      </el-checkbox>
    </div>
    <div class="upload-hint">
      支持 PDF / 图片 / Word，单文件不超过 20MB；换证上传后旧版本自动留档
    </div>
    <el-table
      v-loading="loading"
      :data="attachments"
      border
      class="mt12"
      data-test="attachment-table"
    >
      <el-table-column prop="file_name" label="文件名" min-width="180" />
      <el-table-column label="版本" width="96">
        <template #default="{ row }">
          <el-tag v-if="row.is_current" type="success" size="small">v{{ row.version }} 当前</el-tag>
          <el-tag v-else type="info" size="small">v{{ row.version }} 历史</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="90">
        <template #default="{ row }">{{ humanSize(row.size) }}</template>
      </el-table-column>
      <el-table-column label="上传时间" width="160">
        <template #default="{ row }">
          {{ String(row.created_at).replace('T', ' ').slice(0, 19) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.previewable"
            link
            type="primary"
            data-test="btn-preview"
            @click="openPreview(row)"
          >
            预览
          </el-button>
          <el-button link type="primary" data-test="btn-download" @click="download(row)">
            下载
          </el-button>
          <el-button link type="danger" data-test="btn-del-attachment" @click="remove(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && attachments.length === 0" description="暂无扫描件" />
  </el-drawer>

  <GspAttachmentPreview v-model="previewVisible" :attachment="previewTarget" />
</template>

<style scoped>
.drawer-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
}
.upload-hint {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}
.mt12 {
  margin-top: 12px;
}
</style>
