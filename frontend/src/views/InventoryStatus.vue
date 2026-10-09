<script setup lang="ts">
import { onMounted, ref } from 'vue'

import request from '@/utils/request'

interface Row {
  id: number
  warehouse_name: string
  sku: string
  product_name: string
  category_name: string | null
  quantity: number
  safety_stock: number
  stock_status: string
  stock_value: number
}

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

const statusTagMap: Record<string, { type: 'success' | 'warning' | 'danger' }> = {
  库存充足: { type: 'success' },
  库存预警: { type: 'warning' },
  库存不足: { type: 'danger' },
}

async function load() {
  loading.value = true
  try {
    const data = (await request.get('/reports/inventory-status', {
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
