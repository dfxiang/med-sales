<script setup lang="ts">
import { useRouter } from 'vue-router'

import CrudPage from '@/components/CrudPage.vue'
import { supplierApi } from '@/api/supplier'
import { statusTagMap, supplierStatusOptions } from '@/utils/constants'

const router = useRouter()

function openQualification(row: Record<string, unknown>) {
  router.push({
    path: '/gsp/qualification',
    query: { entity_type: 'supplier', entity_id: String(row.id) },
  })
}

const config = {
  title: '供应商管理',
  api: supplierApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '编码', width: 110 },
    { prop: 'name', label: '供应商名称', width: 330 },
    { prop: 'contact_person', label: '联系人', width: 110 },
    { prop: 'credit_days', label: '账期(天)', width: 100 },
    { prop: 'status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 110 },
    { prop: 'phone', label: '电话', width: 130 },
  ],
  searchFields: [
    { prop: 'keyword', label: '关键词' },
    { prop: 'status', label: '状态', type: 'select', options: supplierStatusOptions },
  ],
  formFields: [
    { prop: 'code', label: '编码', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '供应商名称', type: 'input', required: true, span: 12 },
    { prop: 'contact_person', label: '联系人', type: 'input', span: 12 },
    { prop: 'phone', label: '电话', type: 'input', span: 12 },
    { prop: 'credit_days', label: '账期天数', type: 'number', default: 30, span: 12 },
    { prop: 'status', label: '状态', type: 'select', default: '合作中', options: supplierStatusOptions, span: 12 },
    { prop: 'province', label: '省份', type: 'input', span: 12 },
    { prop: 'city', label: '城市', type: 'input', span: 12 },
    { prop: 'address', label: '地址', type: 'input' },
    { prop: 'email', label: '邮箱', type: 'input' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config">
    <template #actions="{ row }">
      <el-button link type="primary" data-test="btn-qualification" @click="openQualification(row)">
        资质
      </el-button>
    </template>
  </CrudPage>
</template>
