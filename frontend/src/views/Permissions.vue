<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { permissionApi } from '@/api/system'
import { permissionModuleLabel } from '@/utils/permission'

const config = {
  title: '权限管理',
  api: permissionApi,
  // 新增/编辑/删除需要的权限；无此权限时按钮自动隐藏（后端仍会校验）
  managePermission: 'system:permission:manage',
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '权限编码', width: 200 },
    {
      prop: 'module',
      label: '模块',
      width: 120,
      formatter: (row: Record<string, unknown>) => permissionModuleLabel(String(row.code ?? '')),
    },
    { prop: 'name', label: '权限名称', width: 170 },
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
