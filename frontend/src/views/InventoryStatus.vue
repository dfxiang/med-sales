<script setup lang="ts">
import { onMounted, ref } from 'vue'

import request from '@/utils/request'

interface Row {
  warehouse_name: string
  sku: string
  product_name: string
  category_name: string
  quantity: number
  safety_stock: number
  stock_diff: number
  stock_status: string
  stock_value: number
}

const rows = ref<Row[]>([])

const statusTagMap: Record<string, { type: 'success' | 'warning' | 'danger' }> = {
  库存充足: { type: 'success' },
  库存预警: { type: 'warning' },
  库存不足: { type: 'danger' },
}

onMounted(async () => {
  rows.value = (await request.get('/reports/inventory-status')) as Row[]
})
</script>

<template>
  <el-card>
    <template #header><span>库存状态报表</span></template>
    <el-table :data="rows" border stripe>
      <el-table-column prop="warehouse_name" label="仓库" width="150" />
      <el-table-column prop="sku" label="SKU" width="140" />
      <el-table-column prop="product_name" label="商品名称" min-width="180" />
      <el-table-column prop="category_name" label="分类" width="120" />
      <el-table-column prop="quantity" label="当前库存" width="100" />
      <el-table-column prop="safety_stock" label="安全库存" width="100" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.stock_status]?.type || 'info'">{{ row.stock_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="库存价值" min-width="130">
        <template #default="{ row }">{{ Number(row.stock_value).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
