<script setup lang="ts">
import CrudPage from '@/components/CrudPage.vue'
import { categoryApi, manufacturerApi, productApi } from '@/api/product'
import { supplierApi } from '@/api/supplier'
import { storageOptions } from '@/utils/constants'

const config = {
  title: '商品管理',
  api: productApi,
  columns: [
    { prop: 'id', label: 'ID', width: 70 },
    { prop: 'sku', label: 'SKU', width: 140 },
    { prop: 'name', label: '商品名称', width: 220 },
    { prop: 'category_id', label: '分类 ID', width: 90 },
    { prop: 'specification', label: '规格', width: 150 },
    { prop: 'unit', label: '单位', width: 80 },
    { prop: 'storage_condition', label: '储存条件', width: 110 },
    { prop: 'cost_price', label: '成本价', type: 'money', width: 110 },
    { prop: 'standard_price', label: '标准售价', type: 'money', width: 110 },
    { prop: 'is_active', label: '在售' },
  ],
  searchFields: [
    { prop: 'keyword', label: '关键词' },
    { prop: 'category_id', label: '分类 ID', type: 'input' },
  ],
  formFields: [
    { prop: 'sku', label: 'SKU', type: 'input', required: true, span: 12 },
    { prop: 'name', label: '商品名称', type: 'input', required: true, span: 12 },
    {
      prop: 'category_id', label: '分类', type: 'select', required: true, span: 12,
      optionsApi: () => categoryApi.list({ page: 1, size: 200 }).then((d: { items: Record<string, unknown>[] }) => d.items),
    },
    {
      prop: 'manufacturer_id', label: '生产厂家', type: 'select', required: true, span: 12,
      optionsApi: () => manufacturerApi.list({ page: 1, size: 200 }).then((d: { items: Record<string, unknown>[] }) => d.items),
    },
    {
      prop: 'supplier_id', label: '主要供应商', type: 'select', required: true, span: 12,
      optionsApi: () => supplierApi.list({ page: 1, size: 200 }).then((d: { items: Record<string, unknown>[] }) => d.items),
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
  <CrudPage v-bind="config" />
</template>
