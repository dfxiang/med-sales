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

onMounted(async () => {
  rows.value = (await receivableApi.list({})) as ReceivableRow[]
})
</script>

<template>
  <el-card>
    <template #header><span>应收账龄</span></template>
    <el-table :data="rows" border stripe>
      <el-table-column prop="customer_name" label="客户" width="180" />
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
  </el-card>
</template>

<style scoped>
.receivable {
  color: #f56c6c;
  font-weight: 600;
}
</style>
