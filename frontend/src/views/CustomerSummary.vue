<script setup lang="ts">
import { onMounted, ref } from 'vue'

import CustomerSelect from '@/components/CustomerSelect.vue'
import request from '@/utils/request'

interface Row {
  customer_id: number
  customer_code: string
  customer_name: string
  customer_type: string
  coop_level: string
  order_count: number
  total_amount: number
  cost_amount: number
  profit_amount: number
  last_order_date: string | null
}

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const customerId = ref<number | undefined>(undefined)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    if (customerId.value) params.customer_id = customerId.value
    const data = (await request.get('/reports/customer-summary', { params })) as {
      items: Row[]
      total: number
    }
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function onReset() {
  customerId.value = undefined
  onSearch()
}

onMounted(load)
</script>

<template>
  <el-card>
    <el-form inline>
      <el-form-item label="客户">
        <CustomerSelect v-model="customerId" width="220px" data-test="filter-customer" @change="onSearch" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
        <el-button data-test="btn-reset" @click="onReset">重置</el-button>
      </el-form-item>
    </el-form>
    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="customer_code" label="编码" width="110" />
      <el-table-column prop="customer_name" label="客户名称" min-width="240" />
      <el-table-column prop="customer_type" label="类型" width="130" />
      <el-table-column prop="coop_level" label="合作等级" width="110" />
      <el-table-column prop="order_count" label="订单数" width="90" />
      <el-table-column label="销售额" min-width="130">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="毛利" min-width="130">
        <template #default="{ row }">{{ Number(row.profit_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column prop="last_order_date" label="最近下单" width="120" />
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="size"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      class="pagination"
      @current-change="load"
      @size-change="onSearch"
    />
  </el-card>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
