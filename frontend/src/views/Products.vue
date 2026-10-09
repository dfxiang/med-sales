<script setup lang="ts">
import { useRouter } from 'vue-router'

import CrudPage from '@/components/CrudPage.vue'
import { productApi } from '@/api/product'
import { storageOptions } from '@/utils/constants'
import { fetchAllOptions } from '@/utils/options'

const router = useRouter()

function openQualification(row: Record<string, unknown>) {
  router.push({
    path: '/gsp/qualification',
    query: { entity_type: 'product', entity_id: String(row.id) },
  })
}

const config = {
  title: '商品管理',
  api: productApi,
  managePermission: 'product:manage',
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'sku', label: 'SKU', width: 140 },
    { prop: 'name', label: '商品名称', width: 330 },
    { prop: 'category_name', label: '分类', width: 120 },
    { prop: 'specification', label: '规格', width: 150 },
    { prop: 'unit', label: '单位', width: 80 },
    { prop: 'storage_condition', label: '储存条件', width: 110 },
    { prop: 'cost_price', label: '成本价', type: 'money', width: 110 },
    { prop: 'standard_price', label: '标准售价', type: 'money', width: 110 },
    { prop: 'is_active', label: '在售' },
  ],
  searchFields: [
    { prop: 'keyword', label: '关键词', placeholder: '名称 / SKU / 批准文号' },
    {
      prop: 'category_id', label: '分类', type: 'select',
      optionsApi: () => fetchAllOptions<Record<string, unknown>>('/categories'),
    },
  ],
  formFields: [
    { prop: 'sku', label: 'SKU', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '商品名称', type: 'input', required: true, span: 12 },
    {
      prop: 'category_id', label: '分类', type: 'select', required: true, span: 12,
      optionsApi: () => fetchAllOptions<Record<string, unknown>>('/categories'),
    },
    {
      prop: 'manufacturer_id', label: '生产厂家', type: 'select', required: true, span: 12,
      optionsApi: () => fetchAllOptions<Record<string, unknown>>('/manufacturers'),
    },
    {
      prop: 'supplier_id', label: '主要供应商', type: 'select', required: true, span: 12,
      optionsApi: () => fetchAllOptions<Record<string, unknown>>('/suppliers'),
    },
    { prop: 'approval_no', label: '批准文号', type: 'input', span: 12 },
    { prop: 'specification', label: '规格', type: 'input', span: 12 },
    { prop: 'unit', label: '单位', type: 'input', default: '盒', span: 12 },
    { prop: 'dosage_form', label: '剂型', type: 'input', span: 12 },
    { prop: 'storage_condition', label: '储存条件', type: 'select', default: '常温', options: storageOptions, span: 12 },
    { prop: 'is_cold_chain', label: '需冷链运输', type: 'switch', default: false, span: 12 },
    { prop: 'shelf_life_months', label: '有效期(月)', type: 'number', default: 24, span: 12 },
    { prop: 'cost_price', label: '成本价', type: 'number', required: true, span: 12 },
    { prop: 'standard_price', label: '标准售价', type: 'number', required: true, span: 12 },
    { prop: 'is_active', label: '在售', type: 'switch', default: true, span: 12 },
    { prop: 'listed_date', label: '上市日期', type: 'date', required: true, span: 12 },
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
