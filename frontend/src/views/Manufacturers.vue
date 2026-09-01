<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { manufacturerApi } from '@/api/product'

const config = {
  title: '生产厂家',
  api: manufacturerApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'name', label: '厂家名称', width: 220 },
    { prop: 'country', label: '国家/地区', width: 120 },
    { prop: 'description', label: '简介' },
  ],
  searchFields: [{ prop: 'keyword', label: '厂家名称' }],
  formFields: [
    { prop: 'name', label: '厂家名称', type: 'input', required: true },
    { prop: 'country', label: '国家/地区', type: 'input', span: 12 },
    { prop: 'description', label: '简介', type: 'textarea' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" />
</template>
