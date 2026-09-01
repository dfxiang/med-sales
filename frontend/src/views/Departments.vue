<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { departmentApi } from '@/api/org'

const config = {
  title: '部门管理',
  api: departmentApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '部门编码', width: 120 },
    { prop: 'name', label: '部门名称', width: 180 },
    { prop: 'description', label: '职责说明' },
  ],
  searchFields: [{ prop: 'keyword', label: '关键词' }],
  formFields: [
    { prop: 'code', label: '部门编码', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '部门名称', type: 'input', required: true, span: 12 },
    { prop: 'description', label: '职责说明', type: 'textarea' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" />
</template>
