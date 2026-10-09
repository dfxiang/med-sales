<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { receivableApi } from '@/api/finance'

interface ReceivableRow {
  customer_id: number
  customer_name: string
  order_id: number
  order_no: string
  order_date: string
  total_amount: number
  paid_amount: number
  receivable: number
  settlement_method: string
  days_overdue: number
}

const rows = ref<ReceivableRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = (await receivableApi.list({ page: page.value, size: size.value })) as unknown as {
      items: ReceivableRow[]
      total: number
    }
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
      <el-table-column prop="customer_name" label="客户" width="230" />
      <el-table-column prop="order_no" label="订单号" width="180" />
      <el-table-column prop="order_date" label="下单日期" width="120" />
      <el-table-column label="应收金额" width="140">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="已收金额" width="140">
        <template #default="{ row }">{{ Number(row.paid_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="未收金额" width="140">
        <template #default="{ row }">
          <span class="receivable">{{ Number(row.receivable).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="settlement_method" label="结算方式" width="120" />
      <el-table-column label="逾期天数" width="100">
        <template #default="{ row }">
          <el-tag :type="row.days_overdue > 0 ? 'danger' : 'success'">{{ row.days_overdue }} 天</el-tag>
        </template>
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
.receivable {
  color: #f56c6c;
  font-weight: 600;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
