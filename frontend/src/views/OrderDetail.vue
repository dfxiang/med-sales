<script setup lang="ts">
import { onMounted, ref } from 'vue'

import request from '@/utils/request'
import { fetchAllOptions } from '@/utils/options'

interface Row {
  order_id: number
  order_no: string
  order_date: string
  order_status: string
  customer_name: string
  employee_name: string
  department_name: string | null
  warehouse_name: string
  sku: string
  product_name: string
  quantity: number
  unit_price: number
  line_amount: number
  order_amount: number
  paid_amount: number
}

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filters = ref<Record<string, unknown>>({})
const customers = ref<{ id: number; name: string }[]>([])

const statusTagMap: Record<string, { type: 'success' | 'warning' | 'danger' | 'info' | 'primary' }> = {
  待付款: { type: 'warning' },
  已发货: { type: 'primary' },
  已完成: { type: 'success' },
  已取消: { type: 'info' },
}

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (filters.value.customer_id) params.customer_id = filters.value.customer_id
  if (filters.value.status) params.status = filters.value.status
  if (filters.value.start_date) params.start_date = filters.value.start_date
  if (filters.value.end_date) params.end_date = filters.value.end_date
  const data = (await request.get('/reports/order-detail', { params })) as { items: Row[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(async () => {
  load()
  customers.value = await fetchAllOptions<{ id: number; name: string }>('/customers')
})
</script>

<template>
  <el-card>
    <el-form inline>
      <el-form-item label="客户">
        <el-select v-model="filters.customer_id" clearable filterable placeholder="请选择客户" style="width: 200px">
          <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" clearable placeholder="请选择状态" style="width: 140px">
          <el-option v-for="s in ['待付款', '已发货', '已完成', '已取消']" :key="s" :label="s" :value="s" />
        </el-select>
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="filters.start_date" type="date" value-format="YYYY-MM-DD" style="width: 150px" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="filters.end_date" type="date" value-format="YYYY-MM-DD" style="width: 150px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="rows" border stripe>
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="order_date" label="日期" width="110" />
      <el-table-column prop="customer_name" label="客户" width="150" />
      <el-table-column prop="employee_name" label="销售员" width="90" />
      <el-table-column prop="product_name" label="商品" min-width="150" />
      <el-table-column prop="quantity" label="数量" width="80" />
      <el-table-column label="行金额" width="110">
        <template #default="{ row }">{{ Number(row.line_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="订单金额" width="120">
        <template #default="{ row }">{{ Number(row.order_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.order_status]?.type || 'info'">{{ row.order_status }}</el-tag>
        </template>
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
