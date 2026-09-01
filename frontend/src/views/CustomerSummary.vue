<script setup lang="ts">
import { onMounted, ref } from 'vue'

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

onMounted(async () => {
  rows.value = ((await request.get('/reports/customer-summary')) as Row[]).sort(
    (a, b) => b.total_amount - a.total_amount,
  )
})
</script>

<template>
  <el-card>
    <template #header><span>客户销售汇总</span></template>
    <el-table :data="rows" border stripe>
      <el-table-column prop="customer_code" label="编码" width="110" />
      <el-table-column prop="customer_name" label="客户名称" min-width="200" />
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
  </el-card>
</template>
