<script setup lang="ts">
import { onMounted, ref } from 'vue'

import CategorySelect from '@/components/CategorySelect.vue'
import ManufacturerSelect from '@/components/ManufacturerSelect.vue'
import ProductSelect from '@/components/ProductSelect.vue'
import request from '@/utils/request'

interface Row {
  product_id: number
  sku: string
  product_name: string
  category_name: string | null
  manufacturer_name: string | null
  sold_quantity: number
  sales_amount: number
  gross_profit: number
  order_count: number
}

interface Filters {
  product_id?: number
  category_id?: number
  manufacturer_id?: number
}

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
// 统一业务对象筛选：商品 / 分类 / 厂家（本报表的行就是商品，行上没有客户维度）
const filters = ref<Filters>({})
// 请求序号：汇总聚合较慢，筛选后若旧请求晚到，不能把新结果覆盖回全量数据
let loadSeq = 0

async function load() {
  const seq = ++loadSeq
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    if (filters.value.product_id) params.product_id = filters.value.product_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.manufacturer_id) params.manufacturer_id = filters.value.manufacturer_id
    const data = (await request.get('/reports/product-summary', { params })) as {
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

function onSizeChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
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
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
          <el-button data-test="btn-reset" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column prop="sku" label="SKU" width="140" />
      <el-table-column prop="product_name" label="商品名称" min-width="240" />
      <el-table-column prop="category_name" label="分类" width="120" />
      <el-table-column prop="manufacturer_name" label="厂家" width="140" />
      <el-table-column prop="sold_quantity" label="销量" width="100" />
      <el-table-column prop="order_count" label="订单数" width="90" />
      <el-table-column label="销售额" min-width="130">
        <template #default="{ row }">{{ Number(row.sales_amount).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="毛利" min-width="130">
        <template #default="{ row }">{{ Number(row.gross_profit).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="size"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      class="pagination"
      @current-change="load"
      @size-change="onSizeChange"
    />
  </el-card>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
