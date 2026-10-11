<script setup lang="ts">
import { onMounted, ref } from 'vue'

import CategorySelect from '@/components/CategorySelect.vue'
import ManufacturerSelect from '@/components/ManufacturerSelect.vue'
import ProductSelect from '@/components/ProductSelect.vue'
import request from '@/utils/request'

interface Row {
  id: number
  warehouse_name: string
  sku: string
  product_name: string
  category_name: string | null
  quantity: number
  safety_stock: number
  stock_status: string
  stock_value: number
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
// 统一业务对象筛选：商品 / 分类 / 厂家（库存没有客户维度，不做客户筛选）
const filters = ref<Filters>({})
// 请求序号：筛选后旧请求晚到时不能覆盖新结果
let loadSeq = 0

const statusTagMap: Record<string, { type: 'success' | 'warning' | 'danger' }> = {
  库存充足: { type: 'success' },
  库存预警: { type: 'warning' },
  库存不足: { type: 'danger' },
}

async function load() {
  const seq = ++loadSeq
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    if (filters.value.product_id) params.product_id = filters.value.product_id
    if (filters.value.category_id) params.category_id = filters.value.category_id
    if (filters.value.manufacturer_id) params.manufacturer_id = filters.value.manufacturer_id
    const data = (await request.get('/reports/inventory-status', { params })) as {
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
      <el-table-column prop="warehouse_name" label="仓库" width="150" />
      <el-table-column prop="sku" label="SKU" width="140" />
      <el-table-column prop="product_name" label="商品名称" min-width="180" />
      <el-table-column prop="category_name" label="分类" width="120" />
      <el-table-column prop="quantity" label="当前库存" width="100" />
      <el-table-column prop="safety_stock" label="安全库存" width="100" />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.stock_status]?.type || 'info'">{{ row.stock_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="库存价值" min-width="130">
        <template #default="{ row }">{{ Number(row.stock_value).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</template>
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
