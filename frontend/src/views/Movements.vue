<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { inventoryApi } from '@/api/inventory'

interface MovementRow {
  id: number
  movement_type: string
  quantity: number
  movement_date: string
  remark: string | null
  ref_table: string | null
  created_at: string
}

const rows = ref<MovementRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filters = ref<Record<string, unknown>>({})

const typeTagMap: Record<string, { type: 'success' | 'warning' | 'danger' | 'primary' }> = {
  期初入库: { type: 'info' },
  采购入库: { type: 'success' },
  销售出库: { type: 'danger' },
  退货入库: { type: 'warning' },
}

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (filters.value.movement_type) params.movement_type = filters.value.movement_type
  if (filters.value.product_id) params.product_id = filters.value.product_id
  const data = (await inventoryApi.movements(params)) as { items: MovementRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <el-form inline>
      <el-form-item label="类型">
        <el-select v-model="filters.movement_type" clearable placeholder="请选择类型" style="width: 150px">
          <el-option v-for="t in ['期初入库', '采购入库', '销售出库', '退货入库']" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="商品 ID">
        <el-input v-model="filters.product_id" placeholder="请输入商品 ID" style="width: 120px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="rows" border stripe>
      <el-table-column prop="id" label="ID" width="90" />
      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          <el-tag :type="typeTagMap[row.movement_type]?.type || 'info'">{{ row.movement_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="product_id" label="商品 ID" width="100" />
      <el-table-column prop="quantity" label="数量" width="100" />
      <el-table-column prop="movement_date" label="变动日期" width="120" />
      <el-table-column prop="ref_table" label="来源单据" width="160" />
      <el-table-column prop="remark" label="备注" min-width="180" />
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ String(row.created_at).replace('T', ' ').slice(0, 19) }}</template>
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
