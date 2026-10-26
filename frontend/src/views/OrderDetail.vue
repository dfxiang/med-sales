<script setup lang="ts">
import { onMounted, ref } from 'vue'

import CategorySelect from '@/components/CategorySelect.vue'
import CustomerSelect from '@/components/CustomerSelect.vue'
import ManufacturerSelect from '@/components/ManufacturerSelect.vue'
import ProductSelect from '@/components/ProductSelect.vue'
import request from '@/utils/request'

interface Row {
  order_id: number
  order_no: string
  order_date: string
  order_status: string
  customer_name: string
  employee_name: string
  department_name: string | null
  warehouse_name: string
  sku: string
  product_name: string
  quantity: number
  unit_price: number
  line_amount: number
  order_amount: number
  paid_amount: number
}

interface Filters {
  order_no?: string
  product_id?: number
  category_id?: number
  manufacturer_id?: number
  customer_id?: number
  status?: string
  start_date?: string
  end_date?: string
}

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
// 统一业务对象筛选：商品 / 分类 / 厂家 / 客户（控件传的都是主键）
const filters = ref<Filters>({})
// 请求序号：筛选后旧请求晚到时不能覆盖新结果
let loadSeq = 0

const statusTagMap: Record<string, { type: 'success' | 'warning' | 'danger' | 'info' | 'primary' }> = {
  待付款: { type: 'warning' },
  已发货: { type: 'primary' },
  已完成: { type: 'success' },
  已取消: { type: 'info' },
}

async function load() {
  const seq = ++loadSeq
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    if (filters.value.order_no?.trim()) params.order_no = filters.value.order_no.trim()
    if (filters.value.product_id) params.product_id = filters.value.product_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.manufacturer_id) params.manufacturer_id = filters.value.manufacturer_id
    if (filters.value.customer_id) params.customer_id = filters.value.customer_id
    if (filters.value.status) params.status = filters.value.status
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date
    const data = (await request.get('/reports/order-detail', { params })) as {
      items: Row[]
      total: number
    }
    if (seq !== loadSeq) return
    rows.value = data.items
    total.value = data.total
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function onReset() {
  filters.value = {}
  onSearch()
}

onMounted(load)
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
        <el-form-item label="订单号">
          <el-input
            v-model="filters.order_no"
            clearable
            placeholder="请输入订单号"
            data-test="filter-order-no"
            style="width: 200px"
            @keyup.enter="onSearch"
            @clear="onSearch"
          />
        </el-form-item>
        <el-form-item label="商品">
          <ProductSelect
            v-model="filters.product_id"
            width="240px"
            data-test="filter-product"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="分类">
          <CategorySelect
            v-model="filters.category_id"
            width="200px"
            data-test="filter-category"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="厂家">
          <ManufacturerSelect
            v-model="filters.manufacturer_id"
            width="200px"
            data-test="filter-manufacturer"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="客户">
          <CustomerSelect
            v-model="filters.customer_id"
            width="240px"
            data-test="filter-customer"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.status"
            clearable
            placeholder="请选择状态"
            style="width: 140px"
            @change="onSearch"
          >
            <el-option v-for="s in ['待付款', '已发货', '已完成', '已取消']" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="filters.start_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 150px"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="filters.end_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 150px"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
          <el-button data-test="btn-reset" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="order_no" label="订单号" width="170" />
      <el-table-column prop="order_date" label="日期" width="110" />
      <el-table-column prop="customer_name" label="客户" width="200" />
      <el-table-column prop="employee_name" label="销售员" width="90" />
      <el-table-column prop="product_name" label="商品" min-width="180" />
      <el-table-column prop="quantity" label="数量" width="80" />
      <el-table-column label="行金额" width="110">
        <template #default="{ row }">{{ Number(row.line_amount).toLocaleString($intlLocale(), { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="订单金额" width="120">
        <template #default="{ row }">{{ Number(row.order_amount).toLocaleString($intlLocale(), { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.order_status]?.type || 'info'">{{ row.order_status }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSearch" />
  </el-card>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
