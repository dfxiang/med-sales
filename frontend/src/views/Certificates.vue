<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
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
</script>
<template>
  <CrudPage v-bind="config" />
</template>
