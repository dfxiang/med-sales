<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import CrudPage from '@/components/CrudPage.vue'
import GspAttachmentDrawer from '@/components/GspAttachmentDrawer.vue'
import { certificateApi, type Certificate } from '@/api/gsp'
import {
  certStatusTagMap,
  certTypeOptions,
  entityTypeOptions,
  reviewStatusOptions,
} from '@/utils/constants'
import { getEntityOption, searchEntityOptions } from '@/utils/gsp'

const router = useRouter()
const pageRef = ref<{ reload: () => void } | null>(null)

const entityTypeTagMap = {
  customer: { text: '客户', type: 'info' as const },
  supplier: { text: '供应商', type: 'primary' as const },
  product: { text: '商品', type: 'success' as const },
  manufacturer: { text: '生产厂家', type: 'warning' as const },
}

const config = {
  title: '证照',
  managePermission: 'gsp:manage',
  // 操作列含「通过/驳回/扫描件/档案/编辑/删除」，200px 会换行，放宽到 500px
  actionColumnWidth: 500,
  api: {
    list: (params: Record<string, unknown>) => certificateApi.list(params),
    create: (data: Record<string, unknown>) => certificateApi.create(data),
    update: (id: number, data: Record<string, unknown>) => certificateApi.update(id, data),
    remove: (id: number) => certificateApi.remove(id),
  },
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    {
      prop: 'entity_type',
      label: '对象类型',
      type: 'tag' as const,
      tagMap: entityTypeTagMap,
      width: 100,
    },
    { prop: 'entity_name', label: '关联对象', width: 270 },
    { prop: 'cert_type', label: '证照类型', width: 160 },
    { prop: 'cert_no', label: '证照编号', width: 170 },
    { prop: 'valid_from', label: '生效日期', type: 'date' as const, width: 110 },
    { prop: 'valid_to', label: '到期日期', type: 'date' as const, width: 110 },
    {
      prop: 'effective_status',
      label: '状态',
      type: 'tag' as const,
      tagMap: certStatusTagMap,
      width: 100,
    },
    { prop: 'attachment_count', label: '扫描件', width: 90 },
  ],
  searchFields: [
    { prop: 'keyword', label: '证照类型/编号' },
    {
      prop: 'entity_type',
      label: '对象类型',
      type: 'select' as const,
      options: entityTypeOptions,
    },
    {
      prop: 'review_status',
      label: '审核状态',
      type: 'select' as const,
      options: reviewStatusOptions,
    },
  ],
  formFields: [
    {
      prop: 'entity_type',
      label: '对象类型',
      type: 'select' as const,
      required: true,
      options: entityTypeOptions,
      span: 12,
    },
    {
      prop: 'entity_id',
      label: '关联对象',
      type: 'remote-select' as const,
      required: true,
      span: 12,
      remoteDepends: ['entity_type'],
      remoteApi: (keyword: string, form: Record<string, unknown>) =>
        searchEntityOptions(String(form.entity_type ?? ''), keyword),
      remoteById: (value: string | number, form: Record<string, unknown>) =>
        getEntityOption(String(form.entity_type ?? ''), Number(value)),
      placeholder: '输入名称/编码搜索',
    },
    {
      prop: 'cert_type',
      label: '证照类型',
      type: 'select' as const,
      required: true,
      allowCreate: true,
      options: certTypeOptions,
      span: 12,
    },
    { prop: 'cert_no', label: '证照编号', type: 'input' as const, span: 12 },
    { prop: 'valid_from', label: '生效日期', type: 'date' as const, span: 12 },
    { prop: 'valid_to', label: '到期日期', type: 'date' as const, span: 12 },
    { prop: 'remark', label: '备注', type: 'textarea' as const },
  ],
}

const filesVisible = ref(false)
const currentCert = ref<Certificate | null>(null)

function openFiles(row: Record<string, unknown>) {
  currentCert.value = row as unknown as Certificate
  filesVisible.value = true
}

async function approve(row: Record<string, unknown>) {
  const cert = row as unknown as Certificate
  const { value } = await ElMessageBox.prompt(
    `确认通过「${cert.cert_type}」的首营资料审核？`,
    '审核通过',
    { inputPlaceholder: '审核意见（选填）', confirmButtonText: '通过' },
  )
  await certificateApi.review(cert.id, 'approve', value || undefined)
  ElMessage.success('已通过审核')
  pageRef.value?.reload()
}

async function reject(row: Record<string, unknown>) {
  const cert = row as unknown as Certificate
  const { value } = await ElMessageBox.prompt(
    `请填写「${cert.cert_type}」的驳回原因`,
    '驳回',
    {
      inputPlaceholder: '驳回原因（必填）',
      inputValidator: (text: string) => (text ? true : '请填写驳回原因'),
      confirmButtonText: '驳回',
    },
  )
  await certificateApi.review(cert.id, 'reject', value)
  ElMessage.success('已驳回')
  pageRef.value?.reload()
}

function openProfile(row: Record<string, unknown>) {
  const cert = row as unknown as Certificate
  router.push({
    path: '/gsp/qualification',
    query: { entity_type: cert.entity_type, entity_id: cert.entity_id },
  })
}
</script>

<template>
  <CrudPage ref="pageRef" v-bind="config">
    <template #actions="{ row }">
      <el-button
        v-if="row.review_status === '待审核'"
        v-permission="'gsp:manage'"
        link
        type="success"
        data-test="btn-approve"
        @click="approve(row)"
      >
        通过
      </el-button>
      <el-button
        v-if="row.review_status === '待审核'"
        v-permission="'gsp:manage'"
        link
        type="warning"
        data-test="btn-reject"
        @click="reject(row)"
      >
        驳回
      </el-button>
      <el-button link type="primary" data-test="btn-attachments" @click="openFiles(row)">
        扫描件
      </el-button>
      <el-button link type="info" data-test="btn-profile" @click="openProfile(row)">
        档案
      </el-button>
    </template>
  </CrudPage>

  <GspAttachmentDrawer
    v-model="filesVisible"
    :certificate="currentCert"
    @changed="pageRef?.reload()"
  />
</template>
