<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { batchApi } from '@/api/gsp'
import { statusTagMap } from '@/utils/constants'

const config = {
  title: '批次管理',
  api: batchApi,
  managePermission: 'gsp:manage',
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'product_sku', label: 'SKU', width: 150 },
    { prop: 'product_name', label: '商品名称', width: 240 },
    { prop: 'batch_no', label: '批号', width: 160 },
    { prop: 'production_date', label: '生产日期', type: 'date', width: 120 },
    { prop: 'expiry_date', label: '有效期至', type: 'date', width: 120 },
    { prop: 'quantity', label: '数量', width: 100 },
    { prop: 'status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 100 },
  ],
  searchFields: [
    { prop: 'product_id', label: '商品', type: 'entity', entity: 'product' },
    {
      prop: 'status', label: '状态', type: 'select',
      options: [
        { label: '正常', value: '正常' },
        { label: '过期', value: '过期' },
        { label: '已售罄', value: '已售罄' },
      ],
    },
    { prop: 'keyword', label: '批号' },
  ],
  formFields: [
    { prop: 'product_id', label: '商品', type: 'entity', entity: 'product', required: true },
    { prop: 'batch_no', label: '批号', type: 'input', required: true },
    { prop: 'production_date', label: '生产日期', type: 'date', span: 12 },
    { prop: 'expiry_date', label: '有效期至', type: 'date', span: 12 },
    { prop: 'quantity', label: '数量', type: 'number', default: 0, span: 12 },
    { prop: 'status', label: '状态', type: 'select', default: '正常', options: [{ label: '正常', value: '正常' }, { label: '过期', value: '过期' }, { label: '已售罄', value: '已售罄' }], span: 12 },
    { prop: 'remark', label: '备注', type: 'textarea' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" />
</template>
