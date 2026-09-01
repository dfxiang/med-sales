<script setup lang="ts">
import { onMounted, ref } from 'vue'

import request from '@/utils/request'

interface Row {
  product_id: number
  sku: string
  product_name: string
  category_name: string | null
  manufacturer_name: string | null
  sold_quantity: number
  sales_amount: number
  gross_profit: number
  order_count: number
}

const rows = ref<Row[]>([])

onMounted(async () => {
  rows.value = ((await request.get('/reports/product-summary')) as Row[]).sort(
    (a, b) => b.sales_amount - a.sales_amount,
  )
})
</script>

<template>
  <el-card>
    <template #header><span>商品销售汇总</span></template>
    <el-table :data="rows" border stripe>
      <el-table-column prop="sku" label="SKU" width="140" />
      <el-table-column prop="product_name" label="商品名称" min-width="180" />
      <el-table-column prop="category_name" label="分类" width="120" />
      <el-table-column prop="manufacturer_name" label="厂家" width="140" />
      <el-table-column prop="sold_quantity" label="销量" width="100" />
      <el-table-column prop="order_count" label="订单数" width="90" />
      <el-table-column label="销售额" min-width="130">
        <template #default="{ row }">{{ Number(row.sales_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="毛利" min-width="130">
        <template #default="{ row }">{{ Number(row.gross_profit).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
