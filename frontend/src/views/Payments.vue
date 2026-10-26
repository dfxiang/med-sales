<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { paymentApi } from '@/api/finance'
import CustomerSelect from '@/components/CustomerSelect.vue'
import { paymentMethodOptions } from '@/utils/constants'
import { fetchAllOptions } from '@/utils/options'

interface PaymentRow {
  id: number
  sales_order_id: number
  order_no: string | null
  customer_id: number
  customer_name: string | null
  payment_date: string
  amount: number
  payment_method: string
  status: string
}

const rows = ref<PaymentRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const orders = ref<{ id: number; order_no: string; total_amount: number; paid_amount: number }[]>([])

// 客户筛选：统一的客户选择控件，输入名称可模糊匹配候选
const customerId = ref<number | undefined>(undefined)

// 付款日期区间、订单号
const orderNoInput = ref('')
const startDate = ref('')
const endDate = ref('')

const dialogVisible = ref(false)
const saving = ref(false)
const form = ref<Record<string, unknown>>({ payment_date: new Date().toISOString().slice(0, 10), status: '成功' })

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (customerId.value) {
    params.customer_id = customerId.value
  }
  if (orderNoInput.value.trim()) {
    params.order_no = orderNoInput.value.trim()
  }
  if (startDate.value) params.start_date = startDate.value
  if (endDate.value) params.end_date = endDate.value
  const data = (await paymentApi.list(params)) as { items: PaymentRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSearch() {
  page.value = 1
  load()
}

function onReset() {
  customerId.value = undefined
  orderNoInput.value = ''
  startDate.value = ''
  endDate.value = ''
  onSearch()
}

function onSizeChange() {
  page.value = 1
  load()
}

async function loadOptions() {
  const ord = await fetchAllOptions<{ id: number; order_no: string; total_amount: number; paid_amount: number }>(
    '/sales-orders',
  )
  orders.value = ord.filter(
    (o) => Number(o.paid_amount) < Number(o.total_amount),
  )
}

async function openCreate() {
  form.value = { payment_date: new Date().toISOString().slice(0, 10), status: '成功' }
  dialogVisible.value = true
  // 仅在需要登记收款时才拉未结清订单，避免列表页一进来就请求上百页订单
  await loadOptions()
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
})
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
        <el-form-item label="客户">
          <CustomerSelect v-model="customerId" data-test="filter-customer" @change="onSearch" />
        </el-form-item>
        <el-form-item label="付款开始日期" data-test="filter-start-date">
          <el-date-picker
            v-model="startDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            style="width: 150px"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="付款结束日期" data-test="filter-end-date">
          <el-date-picker
            v-model="endDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            style="width: 150px"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="订单号">
          <el-input
            v-model="orderNoInput"
            clearable
            placeholder="请输入订单号"
            data-test="filter-order-no"
            style="width: 180px"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
          <el-button data-test="btn-reset" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button v-permission="'finance:manage'" type="primary" data-test="btn-create" @click="openCreate">登记收款</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="order_no" label="订单号" width="180">
        <template #default="{ row }">{{ row.order_no || row.sales_order_id }}</template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户" width="330">
        <template #default="{ row }">{{ row.customer_name || row.customer_id }}</template>
      </el-table-column>
      <el-table-column prop="payment_date" label="付款日期" width="120" />
      <el-table-column label="金额" width="140">
        <template #default="{ row }">{{ Number(row.amount).toLocaleString($intlLocale(), { minimumFractionDigits: 2 }) }}</template>
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
