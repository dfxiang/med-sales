<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { paymentApi } from '@/api/finance'
import { paymentMethodOptions } from '@/utils/constants'
import { fetchAllOptions } from '@/utils/options'

interface PaymentRow {
  id: number
  sales_order_id: number
  customer_id: number
  payment_date: string
  amount: number
  payment_method: string
  status: string
}

const rows = ref<PaymentRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const customers = ref<{ id: number; name: string }[]>([])
const orders = ref<{ id: number; order_no: string; total_amount: number; paid_amount: number }[]>([])

const dialogVisible = ref(false)
const saving = ref(false)
const form = ref<Record<string, unknown>>({ payment_date: new Date().toISOString().slice(0, 10), status: '成功' })

async function load() {
  const data = (await paymentApi.list({ page: page.value, size: size.value })) as { items: PaymentRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSizeChange() {
  page.value = 1
  load()
}

async function loadOptions() {
  const [cus, ord] = await Promise.all([
    fetchAllOptions<{ id: number; name: string }>('/customers'),
    fetchAllOptions<{ id: number; order_no: string; total_amount: number; paid_amount: number }>(
      '/sales-orders',
    ),
  ])
  customers.value = cus
  orders.value = ord.filter(
    (o) => Number(o.paid_amount) < Number(o.total_amount),
  )
}

function openCreate() {
  form.value = { payment_date: new Date().toISOString().slice(0, 10), status: '成功' }
  dialogVisible.value = true
}

function onOrderChange(orderId: number) {
  const order = orders.value.find((o) => o.id === orderId)
  if (order) {
    form.value.amount = Number((Number(order.total_amount) - Number(order.paid_amount)).toFixed(2))
  }
}

async function onSubmit() {
  if (!form.value.sales_order_id || !form.value.amount || !form.value.payment_method) {
    ElMessage.warning('请选择订单、填写金额和付款方式')
    return
  }
  saving.value = true
  try {
    await paymentApi.create(form.value)
    ElMessage.success('收款登记成功')
    dialogVisible.value = false
    await load()
    await loadOptions()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  load()
  loadOptions()
})
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <div class="page-toolbar-actions">
        <el-button v-permission="'finance:manage'" type="primary" data-test="btn-create" @click="openCreate">登记收款</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="sales_order_id" label="订单 ID" width="110" />
      <el-table-column label="客户" width="180">
        <template #default="{ row }">{{ customers.find((c) => c.id === row.customer_id)?.name || row.customer_id }}</template>
      </el-table-column>
      <el-table-column prop="payment_date" label="付款日期" width="120" />
      <el-table-column label="金额" width="140">
        <template #default="{ row }">{{ Number(row.amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column prop="payment_method" label="付款方式" width="120" />
      <el-table-column prop="status" label="状态" width="100" />
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSizeChange" />
  </el-card>

  <el-dialog v-model="dialogVisible" title="登记收款" width="520px">
    <el-form :model="form" label-width="100px">
      <el-form-item label="订单" required>
        <el-select
          v-model="form.sales_order_id"
          filterable
          placeholder="请选择未结清订单"
          data-test="field-sales_order_id"
          style="width: 100%"
          @change="(v: number) => onOrderChange(v)"
        >
          <el-option v-for="o in orders" :key="o.id" :label="`${o.order_no}（应收 ${o.total_amount}）`" :value="o.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="付款日期" required>
        <el-date-picker v-model="form.payment_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="金额" required>
        <el-input-number v-model="form.amount" :min="0.01" :precision="2" style="width: 100%" />
      </el-form-item>
      <el-form-item label="付款方式" required>
        <el-select v-model="form.payment_method" placeholder="请选择付款方式" style="width: 100%">
          <el-option v-for="m in paymentMethodOptions" :key="m.value" :label="m.label" :value="m.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.remark" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" data-test="btn-save" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
