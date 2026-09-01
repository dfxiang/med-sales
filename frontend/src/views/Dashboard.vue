<script setup lang="ts">
import { onMounted, ref } from 'vue'

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

onMounted(async () => {
  data.value = (await request.get('/reports/dashboard')) as Dashboard
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
