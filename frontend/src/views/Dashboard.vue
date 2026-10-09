<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import ChartBox from '@/components/ChartBox.vue'
import { alertApi, type GspAlertSummary } from '@/api/gsp'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'

const router = useRouter()
const userStore = useUserStore()

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
const gspAlerts = ref<GspAlertSummary | null>(null)

const gspCards = computed(() => [
  { label: '证照/批次已过期', value: gspAlerts.value?.expired ?? 0, suffix: '项', danger: true },
  { label: '30 天内到期', value: gspAlerts.value?.within_30 ?? 0, suffix: '项', danger: true },
  { label: '待审核资质', value: gspAlerts.value?.pending_review ?? 0, suffix: '项', danger: false },
  { label: '90 天内到期', value: (gspAlerts.value?.within_60 ?? 0) + (gspAlerts.value?.within_90 ?? 0), suffix: '项', danger: false },
])

const monthlyChartOption = computed(() => ({
  title: { text: '月度销售额趋势', textStyle: { fontSize: 14 } },
  tooltip: { trigger: 'axis' },
  grid: { left: 60, right: 30, top: 50, bottom: 40 },
  xAxis: { type: 'category', data: monthly.value.map((r) => r.month) },
  yAxis: { type: 'value' },
  series: [{ name: '销售额', type: 'bar', data: monthly.value.map((r) => r.total_amount), itemStyle: { color: '#409eff' } }],
}))

onMounted(async () => {
  // 按权限取数：缺权限的模块直接跳过，避免登录后满屏 403 提示
  const [d, m, alerts] = await Promise.all([
    userStore.hasPermission('dashboard:view')
      ? (request.get('/reports/dashboard') as Promise<Dashboard>)
      : Promise.resolve(null),
    userStore.hasPermission('report:view')
      ? (request.get('/reports/sales-monthly', { params: { page: 1, size: 6 } }) as Promise<{
          items: { month: string; total_amount: number }[]
        }>)
      : Promise.resolve(null),
    userStore.hasPermission('gsp:view')
      ? (alertApi.summary() as Promise<GspAlertSummary>)
      : Promise.resolve(null),
  ])
  data.value = d
  monthly.value = m?.items ?? []
  gspAlerts.value = alerts
})

function gotoAlerts() {
  router.push('/gsp/alerts')
}
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
    <el-card v-if="userStore.hasPermission('report:view')" data-test="dashboard-chart">
      <template #header><span>月度销售趋势</span></template>
      <ChartBox :option="monthlyChartOption" height="280px" />
    </el-card>
    <el-card v-if="userStore.hasPermission('gsp:view')" data-test="dashboard-gsp">
      <template #header>
        <div class="card-header">
          <span>GSP 合规预警</span>
          <el-button link type="primary" data-test="dashboard-gsp-more" @click="gotoAlerts">
            查看预警中心
          </el-button>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col v-for="card in gspCards" :key="card.label" :span="6">
          <div class="gsp-card" :class="{ 'is-danger': card.danger && card.value > 0 }">
            <div class="stat-label">{{ card.label }}</div>
            <div class="gsp-value">
              {{ Number(card.value).toLocaleString('zh-CN') }}
              <span class="stat-suffix">{{ card.suffix }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.gsp-card {
  padding: 8px 12px;
  border-radius: 6px;
  background: #f5f7fa;
}
.gsp-card.is-danger {
  background: #fef0f0;
}
.gsp-value {
  font-size: 22px;
  font-weight: 600;
  margin-top: 6px;
}
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
