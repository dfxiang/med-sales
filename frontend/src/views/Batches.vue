<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { batchApi } from '@/api/gsp'
import { productApi } from '@/api/product'
import { statusTagMap } from '@/utils/constants'

const config = {
  title: '批次管理',
  api: batchApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'batch_no', label: '批号', width: 160 },
    { prop: 'product_id', label: '商品 ID', width: 90 },
    { prop: 'production_date', label: '生产日期', type: 'date', width: 120 },
    { prop: 'expiry_date', label: '有效期至', type: 'date', width: 120 },
    { prop: 'quantity', label: '数量', width: 100 },
    { prop: 'status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 100 },
  ],
  searchFields: [{ prop: 'product_id', label: '商品 ID', type: 'input' }],
  formFields: [
    {
      prop: 'product_id', label: '商品', type: 'select', required: true,
      optionsApi: () => productApi.list({ page: 1, size: 200 }).then((d: { items: Record<string, unknown>[] }) => d.items),
    },
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
