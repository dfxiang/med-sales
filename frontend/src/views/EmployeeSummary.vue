<script setup lang="ts">
import { onMounted, ref } from 'vue'

import DepartmentSelect from '@/components/DepartmentSelect.vue'
import EmployeeSelect from '@/components/EmployeeSelect.vue'
import request from '@/utils/request'

interface Row {
  employee_id: number
  employee_code: string
  employee_name: string
  department_name: string | null
  position: string | null
  order_count: number
  total_amount: number
  profit_amount: number
  customer_count: number
}

interface Filters {
  employee_id?: number
  department_id?: number
}

const rows = ref<Row[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
// 统一业务对象筛选：销售员（工号 - 姓名）/ 部门；职位只有展示列，不做筛选
const filters = ref<Filters>({})
// 请求序号：筛选后旧请求晚到时不能覆盖新结果
let loadSeq = 0

async function load() {
  const seq = ++loadSeq
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    if (filters.value.employee_id) params.employee_id = filters.value.employee_id
    if (filters.value.department_id) params.department_id = filters.value.department_id
    const data = (await request.get('/reports/employee-summary', { params })) as {
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
        <el-form-item label="销售员">
          <EmployeeSelect
            v-model="filters.employee_id"
            width="240px"
            data-test="filter-employee"
            @change="onSearch"
          />
        </el-form-item>
        <el-form-item label="部门">
          <DepartmentSelect
            v-model="filters.department_id"
            width="220px"
            data-test="filter-department"
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
      <el-table-column prop="employee_code" label="工号" width="100" />
      <el-table-column prop="employee_name" label="姓名" width="120" />
      <el-table-column prop="department_name" label="部门" width="150" />
      <el-table-column prop="position" label="职位" width="140" />
      <el-table-column prop="order_count" label="订单数" width="90" />
      <el-table-column prop="customer_count" label="客户数" width="90" />
      <el-table-column label="销售额" min-width="130">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString($intlLocale(), { maximumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="毛利" min-width="130">
        <template #default="{ row }">{{ Number(row.profit_amount).toLocaleString($intlLocale(), { maximumFractionDigits: 2 }) }}</template>
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
