<script setup lang="ts">
import { useRouter } from 'vue-router'

import CrudPage from '@/components/CrudPage.vue'
import { customerApi } from '@/api/customer'
import { coopLevelOptions, customerTypeOptions, statusTagMap, customerStatusOptions } from '@/utils/constants'

const router = useRouter()

function openQualification(row: Record<string, unknown>) {
  router.push({
    path: '/gsp/qualification',
    query: { entity_type: 'customer', entity_id: String(row.id) },
  })
}

const config = {
  title: '客户管理',
  api: customerApi,
  managePermission: 'customer:manage',
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '客户编码', width: 110 },
    { prop: 'name', label: '客户名称', width: 200 },
    { prop: 'customer_type', label: '客户类型', width: 130 },
    { prop: 'coop_level', label: '合作等级', width: 110 },
    { prop: 'contact_person', label: '联系人', width: 100 },
    { prop: 'province', label: '省份', width: 100 },
    { prop: 'credit_limit', label: '信用额度', type: 'money', width: 130 },
    { prop: 'status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 100 },
  ],
  searchFields: [
    { prop: 'keyword', label: '关键词' },
    { prop: 'customer_type', label: '客户类型', type: 'select', options: customerTypeOptions },
    { prop: 'coop_level', label: '合作等级', type: 'select', options: coopLevelOptions },
    { prop: 'status', label: '状态', type: 'select', options: customerStatusOptions },
  ],
  formFields: [
    { prop: 'code', label: '客户编码', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '客户名称', type: 'input', required: true, span: 12 },
    { prop: 'customer_type', label: '客户类型', type: 'select', default: '单体药房', options: customerTypeOptions, span: 12 },
    { prop: 'coop_level', label: '合作等级', type: 'select', default: '普通客户', options: coopLevelOptions, span: 12 },
    { prop: 'contact_person', label: '联系人', type: 'input', span: 12 },
    { prop: 'phone', label: '电话', type: 'input', span: 12 },
    { prop: 'province', label: '省份', type: 'input', span: 12 },
    { prop: 'city', label: '城市', type: 'input', span: 12 },
    { prop: 'address', label: '地址', type: 'input', span: 12 },
    { prop: 'license_no', label: '证照编号', type: 'input', span: 12 },
    { prop: 'credit_limit', label: '信用额度', type: 'number', default: 0, span: 12 },
    { prop: 'status', label: '状态', type: 'select', default: '正常', options: customerStatusOptions, span: 12 },
    { prop: 'remark', label: '备注', type: 'textarea' },
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
