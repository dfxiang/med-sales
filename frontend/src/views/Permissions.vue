<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { permissionApi } from '@/api/system'

const config = {
  title: '权限管理',
  api: permissionApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '权限编码', width: 180 },
    { prop: 'name', label: '权限名称', width: 180 },
    { prop: 'description', label: '说明' },
  ],
  searchFields: [{ prop: 'keyword', label: '关键词' }],
  formFields: [
    { prop: 'code', label: '权限编码', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '权限名称', type: 'input', required: true, span: 12 },
    { prop: 'description', label: '说明', type: 'textarea' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" />
</template>
