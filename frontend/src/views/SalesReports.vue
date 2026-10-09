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

interface Paged<T> {
  items: T[]
  total: number
}

const daily = ref<DailyRow[]>([])
const dailyTotal = ref(0)
const dailyPage = ref(1)
const dailySize = ref(20)
const dailyChartRows = ref<DailyRow[]>([])

const monthly = ref<MonthlyRow[]>([])
const monthlyTotal = ref(0)
const monthlyPage = ref(1)
const monthlySize = ref(20)
const monthlyChartRows = ref<MonthlyRow[]>([])

async function loadDaily() {
  const data = (await request.get('/reports/sales-daily', {
    params: { page: dailyPage.value, size: dailySize.value },
  })) as Paged<DailyRow>
  daily.value = data.items
  dailyTotal.value = data.total
}

async function loadDailyChart() {
  const data = (await request.get('/reports/sales-daily', {
    params: { page: 1, size: 30 },
  })) as Paged<DailyRow>
  dailyChartRows.value = data.items
}

async function loadMonthly() {
  const data = (await request.get('/reports/sales-monthly', {
    params: { page: monthlyPage.value, size: monthlySize.value },
  })) as Paged<MonthlyRow>
  monthly.value = data.items
  monthlyTotal.value = data.total
}

async function loadMonthlyChart() {
  const data = (await request.get('/reports/sales-monthly', {
    params: { page: 1, size: 200 },
  })) as Paged<MonthlyRow>
  monthlyChartRows.value = data.items
}

async function load() {
  await Promise.all([loadDailyChart(), loadMonthlyChart(), loadDaily(), loadMonthly()])
}

function onDailySizeChange() {
  dailyPage.value = 1
  loadDaily()
}

function onMonthlySizeChange() {
  monthlyPage.value = 1
  loadMonthly()
}

const dailyChartOption = computed(() => ({
  title: { text: '每日销售额趋势（近30天）', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 50, bottom: 40 },
  xAxis: {
    type: 'category',
    data: dailyChartRows.value.map((r) => r.sale_date).reverse(),
  },
  yAxis: { type: 'value' },
  series: [
    {
      name: '销售额',
      type: 'line',
      smooth: true,
      data: dailyChartRows.value.map((r) => r.total_amount).reverse(),
    },
  ],
}))

const monthlyChartOption = computed(() => ({
  title: { text: '月度销售额', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 50, bottom: 40 },
  xAxis: { type: 'category', data: monthlyChartRows.value.map((r) => r.month) },
  yAxis: { type: 'value' },
  series: [
    {
      name: '销售额',
      type: 'bar',
      data: monthlyChartRows.value.map((r) => r.total_amount),
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
      <el-pagination
        v-model:current-page="dailyPage"
        v-model:page-size="dailySize"
        :total="dailyTotal"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="loadDaily"
        @size-change="onDailySizeChange"
      />
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
      <el-pagination
        v-model:current-page="monthlyPage"
        v-model:page-size="monthlySize"
        :total="monthlyTotal"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="loadMonthly"
        @size-change="onMonthlySizeChange"
      />
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
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
