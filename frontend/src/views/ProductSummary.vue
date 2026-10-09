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
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = (await request.get('/reports/product-summary', {
      params: { page: page.value, size: size.value },
    })) as { items: Row[]; total: number }
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSizeChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <el-table v-loading="loading" :data="rows" border stripe>
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
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="size"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      class="pagination"
      @current-change="load"
      @size-change="onSizeChange"
    />
  </el-card>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
