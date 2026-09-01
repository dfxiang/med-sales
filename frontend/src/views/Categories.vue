<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { categoryApi } from '@/api/product'

const config = {
  title: '商品分类',
  api: categoryApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '分类编码', width: 130 },
    { prop: 'name', label: '分类名称', width: 150 },
    { prop: 'sort_order', label: '排序', width: 90 },
    { prop: 'description', label: '说明' },
  ],
  searchFields: [{ prop: 'keyword', label: '关键词' }],
  formFields: [
    { prop: 'code', label: '分类编码', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '分类名称', type: 'input', required: true, span: 12 },
    { prop: 'sort_order', label: '排序', type: 'number', default: 0, span: 12 },
    { prop: 'description', label: '说明', type: 'textarea' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" />
</template>
