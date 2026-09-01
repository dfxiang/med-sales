<script setup lang="ts">
import { onMounted, ref } from 'vue'

import request from '@/utils/request'

interface Row {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  position: string | null
  order_count: number
  total_amount: number
  profit_amount: number
  customer_count: number
}

const rows = ref<Row[]>([])

onMounted(async () => {
  rows.value = ((await request.get('/reports/employee-summary')) as Row[]).sort(
    (a, b) => b.total_amount - a.total_amount,
  )
})
</script>

<template>
  <el-card>
    <template #header><span>销售员业绩汇总</span></template>
    <el-table :data="rows" border stripe>
      <el-table-column prop="employee_code" label="工号" width="100" />
      <el-table-column prop="employee_name" label="姓名" width="120" />
      <el-table-column prop="department_name" label="部门" width="150" />
      <el-table-column prop="position" label="职位" width="140" />
      <el-table-column prop="order_count" label="订单数" width="90" />
      <el-table-column prop="customer_count" label="客户数" width="90" />
      <el-table-column label="销售额" min-width="130">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="毛利" min-width="130">
        <template #default="{ row }">{{ Number(row.profit_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
