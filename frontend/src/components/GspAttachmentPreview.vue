<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { certificateApi, type CertificateAttachment } from '@/api/gsp'

/**
 * 证照扫描件在线预览：API 以 inline 方式回传 S3 对象，这里用浏览器原生能力渲染
 * PDF（内置阅读器）与图片（img），无需引入额外预览库。
 */
const props = defineProps<{
  modelValue: boolean
  attachment: CertificateAttachment | null
}>()

const emit = defineEmits<{ 'update:modelValue': [boolean] }>()

const objectUrl = ref('')
const loading = ref(false)
const kind = ref<'pdf' | 'image' | 'other'>('other')

function release() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
}

async function load() {
  release()
  const attachment = props.attachment
  if (!attachment) return
  kind.value = attachment.kind ?? 'other'
  if (kind.value === 'other') return
  loading.value = true
  try {
    const blob = (await certificateApi.previewAttachment(attachment.id)) as unknown as Blob
    objectUrl.value = URL.createObjectURL(blob)
  } catch {
    // 请求层已提示，这里只需保持预览区为空
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.attachment?.id],
  ([visible]) => {
    if (visible) load()
    else release()
  },
)

onBeforeUnmount(release)

async function download() {
  const attachment = props.attachment
  if (!attachment) return
  const blob = (await certificateApi.downloadAttachment(attachment.id)) as unknown as Blob
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = attachment.file_name
  link.click()
  URL.revokeObjectURL(url)
}

function openInNewTab() {
  if (objectUrl.value) window.open(objectUrl.value, '_blank')
}

function close() {
  emit('update:modelValue', false)
}

function onClosed() {
  release()
  kind.value = 'other'
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="attachment?.file_name || '扫描件预览'"
    width="75%"
    top="5vh"
    class="preview-dialog"
    append-to-body
    @update:model-value="emit('update:modelValue', $event)"
    @closed="onClosed"
  >
    <div v-loading="loading" class="preview-body" data-test="attachment-preview">
      <img
        v-if="objectUrl && kind === 'image'"
        :src="objectUrl"
        :alt="attachment?.file_name || '证照扫描件'"
        class="preview-image"
        data-test="preview-image"
        @click="openInNewTab"
      />
      <iframe
        v-else-if="objectUrl && kind === 'pdf'"
        :src="objectUrl"
        :title="attachment?.file_name || '证照扫描件'"
        class="preview-frame"
        data-test="preview-pdf"
      />
      <el-empty
        v-else-if="!loading"
        description="该格式浏览器不支持在线预览，请下载后查看"
        data-test="preview-unsupported"
      />
    </div>
    <template #footer>
      <span v-if="kind === 'image'" class="preview-hint">点击图片可在新窗口打开</span>
      <el-button v-if="objectUrl && kind === 'image'" @click="openInNewTab">新窗口打开</el-button>
      <el-button data-test="preview-download" @click="download">下载</el-button>
      <el-button type="primary" data-test="preview-close" @click="close">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.preview-body {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
  background: #f5f7fa;
  border-radius: 6px;
}
.preview-image {
  max-width: 100%;
  max-height: 72vh;
  object-fit: contain;
  cursor: zoom-in;
}
.preview-frame {
  width: 100%;
  height: 72vh;
  border: 0;
}
.preview-hint {
  margin-right: auto;
  color: #909399;
  font-size: 12px;
}
:deep(.el-dialog__footer) {
  display: flex;
  align-items: center;
}
</style>
