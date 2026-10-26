<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { inventoryApi } from '@/api/inventory'
import WarehouseSelect from '@/components/WarehouseSelect.vue'

interface InventoryRow {
  id: number
  warehouse_id: number
  product_id: number
  quantity: number
  safety_stock: number
  warehouse_name?: string
  product_name?: string
  sku?: string
  stock_status?: string
  stock_value?: number
}

const rows = ref<InventoryRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filters = ref<Record<string, unknown>>({})

const statusTagMap: Record<string, { type: 'success' | 'warning' | 'danger' | 'info' }> = {
  库存充足: { type: 'success' },
  库存预警: { type: 'warning' },
  库存不足: { type: 'danger' },
}

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (filters.value.warehouse_id) params.warehouse_id = filters.value.warehouse_id
  if (filters.value.status) params.status = filters.value.status
  const data = (await inventoryApi.list(params)) as { items: InventoryRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(async () => {
  load()
})
</script>

<template>
  <el-card>
    <el-form inline>
      <el-form-item label="仓库">
        <WarehouseSelect v-model="filters.warehouse_id" width="200px" data-test="filter-warehouse" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="请选择状态" style="width: 150px">
          <el-option label="库存不足" value="库存不足" />
          <el-option label="库存预警" value="库存预警" />
          <el-option label="库存充足" value="库存充足" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="rows" border stripe>
      <el-table-column prop="warehouse_name" label="仓库" width="160" />
      <el-table-column prop="sku" label="SKU" width="150" />
      <el-table-column prop="product_name" label="商品名称" min-width="180" />
      <el-table-column prop="quantity" label="当前库存" width="110" />
      <el-table-column prop="safety_stock" label="安全库存" width="110" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.stock_status]?.type || 'info'">{{ row.stock_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="库存价值" width="140">
        <template #default="{ row }">{{ Number(row.stock_value || 0).toLocaleString($intlLocale(), { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSearch" />
  </el-card>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
