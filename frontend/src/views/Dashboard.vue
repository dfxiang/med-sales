<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ChartBox from '@/components/ChartBox.vue'
import request from '@/utils/request'

interface Dashboard {
  today_order_count: number
  today_sales_amount: number
  today_profit: number
  month_order_count: number
  month_sales_amount: number
  month_profit: number
  low_stock_count: number
  pending_return_count: number
  total_receivable: number
}

const data = ref<Dashboard | null>(null)
const monthly = ref<{ month: string; total_amount: number }[]>([])

const monthlyChartOption = computed(() => ({
  title: { text: '月度销售额趋势', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 50, bottom: 40 },
  xAxis: { type: 'category', data: monthly.value.map((r) => r.month) },
  yAxis: { type: 'value' },
  series: [{ name: '销售额', type: 'bar', data: monthly.value.map((r) => r.total_amount), itemStyle: { color: '#409eff' } }],
}))

onMounted(async () => {
  const [d, m] = await Promise.all([
    request.get('/reports/dashboard') as Promise<Dashboard>,
    request.get('/reports/sales-monthly', { params: { page: 1, size: 6 } }) as Promise<{
      items: { month: string; total_amount: number }[]
    }>,
  ])
  data.value = d
  monthly.value = m.items
})
</script>

<template>
  <div v-if="data" data-test="dashboard">
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in [
        { label: '今日销售额', value: data.today_sales_amount, suffix: '元' },
        { label: '今日订单数', value: data.today_order_count, suffix: '单' },
        { label: '本月销售额', value: data.month_sales_amount, suffix: '元' },
        { label: '本月毛利', value: data.month_profit, suffix: '元' },
        { label: '库存不足', value: data.low_stock_count, suffix: '项' },
        { label: '待处理退货', value: data.pending_return_count, suffix: '单' },
        { label: '应收总额', value: data.total_receivable, suffix: '元' },
        { label: '本月订单数', value: data.month_order_count, suffix: '单' },
      ]" :key="card.label">
        <el-card class="stat-card">
          <div class="stat-label">{{ card.label }}</div>
          <div class="stat-value">
            {{ Number(card.value).toLocaleString('zh-CN') }} <span class="stat-suffix">{{ card.suffix }}</span>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-card data-test="dashboard-chart">
      <template #header><span>月度销售趋势</span></template>
      <ChartBox :option="monthlyChartOption" height="280px" />
    </el-card>
  </div>
</template>

<style scoped>
.stat-card {
  margin-bottom: 16px;
}
.stat-label {
  color: #909399;
  font-size: 13px;
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
  margin-top: 8px;
}
.stat-suffix {
  font-size: 13px;
  color: #909399;
  font-weight: 400;
}
</style>
