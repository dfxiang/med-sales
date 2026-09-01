<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ChartBox from '@/components/ChartBox.vue'
import request from '@/utils/request'

interface DailyRow {
  sale_date: string
  order_count: number
  quantity: number
  total_amount: number
  discount_amount: number
  cost_amount: number
  profit_amount: number
}

interface MonthlyRow {
  month: string
  order_count: number
  total_amount: number
  profit_amount: number
  amount_growth_rate: number | null
}

const daily = ref<DailyRow[]>([])
const monthly = ref<MonthlyRow[]>([])

async function load() {
  const [d, m] = await Promise.all([
    request.get('/reports/sales-daily') as Promise<DailyRow[]>,
    request.get('/reports/sales-monthly') as Promise<MonthlyRow[]>,
  ])
  daily.value = d
  monthly.value = m
}

const dailyChartOption = computed(() => ({
  title: { text: '每日销售额趋势（近30天）', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 50, bottom: 40 },
  xAxis: { type: 'category', data: daily.value.slice(0, 30).map((r) => r.sale_date).reverse() },
  yAxis: { type: 'value' },
  series: [
    {
      name: '销售额',
      type: 'line',
      smooth: true,
      data: daily.value.slice(0, 30).map((r) => r.total_amount).reverse(),
    },
  ],
}))

const monthlyChartOption = computed(() => ({
  title: { text: '月度销售额', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 50, bottom: 40 },
  xAxis: { type: 'category', data: monthly.value.map((r) => r.month) },
  yAxis: { type: 'value' },
  series: [
    {
      name: '销售额',
      type: 'bar',
      data: monthly.value.map((r) => r.total_amount),
      itemStyle: { color: '#409eff' },
    },
  ],
}))

onMounted(load)
</script>

<template>
  <div>
    <el-card class="mb16" data-test="daily-card">
      <template #header><span>每日销售汇总</span></template>
      <ChartBox :option="dailyChartOption" height="260px" />
      <el-table :data="daily" border stripe size="small" class="mt12">
        <el-table-column prop="sale_date" label="日期" width="120" />
        <el-table-column prop="order_count" label="订单数" width="90" />
        <el-table-column prop="quantity" label="销量" width="110" />
        <el-table-column label="销售额" min-width="130">
          <template #default="{ row }">{{ Number(row.total_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
        </el-table-column>
        <el-table-column label="优惠" min-width="120">
          <template #default="{ row }">{{ Number(row.discount_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
        </el-table-column>
        <el-table-column label="毛利" min-width="130">
          <template #default="{ row }">{{ Number(row.profit_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card data-test="monthly-card">
      <template #header><span>月度销售汇总（含环比）</span></template>
      <ChartBox :option="monthlyChartOption" height="260px" />
      <el-table :data="monthly" border stripe size="small" class="mt12">
        <el-table-column prop="month" label="月份" width="120" />
        <el-table-column prop="order_count" label="订单数" width="90" />
        <el-table-column label="销售额" min-width="130">
          <template #default="{ row }">{{ Number(row.total_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
        </el-table-column>
        <el-table-column label="毛利" min-width="130">
          <template #default="{ row }">{{ Number(row.profit_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
        </el-table-column>
        <el-table-column label="环比增速" min-width="110">
          <template #default="{ row }">
            <el-tag v-if="row.amount_growth_rate !== null" :type="row.amount_growth_rate >= 0 ? 'success' : 'danger'">
              {{ row.amount_growth_rate }}%
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.mb16 {
  margin-bottom: 16px;
}
.mt12 {
  margin-top: 12px;
}
</style>
