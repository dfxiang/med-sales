<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { warehouseApi } from '@/api/warehouse'
import { refreshEntityOptions } from '@/utils/catalogOptions'
import { statusTagMap, warehouseStatusOptions } from '@/utils/constants'

const config = {
  title: '仓库管理',
  api: warehouseApi,
  managePermission: 'warehouse:manage',
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'code', label: '仓库编码', width: 110 },
    { prop: 'name', label: '仓库名称', width: 160 },
    { prop: 'province', label: '省份', width: 100 },
    { prop: 'city', label: '城市', width: 100 },
    { prop: 'manager_name', label: '负责人', width: 110 },
    { prop: 'has_cold_chain', label: '冷链库', width: 90 },
    { prop: 'status', label: '状态', type: 'tag', tagMap: statusTagMap, width: 100 },
  ],
  searchFields: [
    { prop: 'keyword', label: '关键词' },
    { prop: 'status', label: '状态', type: 'select', options: warehouseStatusOptions },
  ],
  formFields: [
    { prop: 'code', label: '仓库编码', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '仓库名称', type: 'input', required: true, span: 12 },
    { prop: 'province', label: '省份', type: 'input', span: 12 },
    { prop: 'city', label: '城市', type: 'input', span: 12 },
    { prop: 'manager_name', label: '负责人', type: 'input', span: 12 },
    { prop: 'phone', label: '电话', type: 'input', span: 12 },
    { prop: 'has_cold_chain', label: '具备冷链库', type: 'switch', default: true, span: 12 },
    { prop: 'status', label: '状态', type: 'select', default: '正常', options: warehouseStatusOptions, span: 12 },
    { prop: 'address', label: '地址', type: 'input' },
  ],
}
</script>
<template>
  <CrudPage v-bind="config" @saved="() => refreshEntityOptions('warehouse')" />
</template>
