<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { returnsApi } from '@/api/returns'
import ItemsEditor, { type ItemRow, type ProductOption } from '@/components/ItemsEditor.vue'
import { returnReasonOptions, statusTagMap } from '@/utils/constants'
import { fetchAllOptions } from '@/utils/options'

interface ReturnRow {
  id: number
  return_no: string
  sales_order_id: number
  customer_id: number
  status: string
  return_date: string
  reason: string | null
  total_amount: number
}

const rows = ref<ReturnRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filters = ref<Record<string, unknown>>({})
const orders = ref<{ id: number; order_no: string }[]>([])
const products = ref<ProductOption[]>([])

const dialogVisible = ref(false)
const saving = ref(false)
const form = ref<Record<string, unknown>>({ return_date: new Date().toISOString().slice(0, 10) })
const itemRows = ref<ItemRow[]>([{ quantity: 1 }])

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value, ...filters.value }
  const data = (await returnsApi.list(params)) as { items: ReturnRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

async function loadOptions() {
  const [ord, prod] = await Promise.all([
    fetchAllOptions<{ id: number; order_no: string }>('/sales-orders'),
    fetchAllOptions<ProductOption>('/products'),
  ])
  orders.value = ord
  products.value = prod
}

function openCreate() {
  form.value = { return_date: new Date().toISOString().slice(0, 10) }
  itemRows.value = [{ quantity: 1 }]
  dialogVisible.value = true
}

function onProductChange(row: ItemRow, product: ProductOption) {
  if (row.unit_price === undefined || row.unit_price === null || row.unit_price === 0) {
    row.unit_price = Number(product.standard_price ?? 0)
  }
}

function totalAmount(): number {
  return itemRows.value.reduce((sum, r) => sum + Number(r.unit_price || 0) * Number(r.quantity || 0), 0)
}

async function onSubmit() {
  if (!form.value.sales_order_id || !form.value.return_date) {
    ElMessage.warning('请选择原订单和退货日期')
    return
  }
  if (!itemRows.value.length || itemRows.value.some((r) => !r.product_id || !r.quantity || !r.unit_price)) {
    ElMessage.warning('请填写至少一条完整明细')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      sales_order_id: form.value.sales_order_id,
      return_date: form.value.return_date,
      reason: form.value.reason || '质量问题',
      items: itemRows.value.map((r) => ({
        product_id: r.product_id,
        quantity: r.quantity,
        unit_price: r.unit_price,
        reason: r.reason || form.value.reason,
      })),
    }
    if (form.value.remark) payload.remark = form.value.remark
    await returnsApi.create(payload)
    ElMessage.success('退货单创建成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onProcess(row: ReturnRow) {
  await ElMessageBox.confirm(`确定处理退货单 ${row.return_no} 并入库吗？`, '提示', { type: 'warning' })
  await returnsApi.process(row.id)
  ElMessage.success('退货处理成功，已入库')
  await load()
}

async function onDelete(row: ReturnRow) {
  await ElMessageBox.confirm('确定删除该退货单吗？', '提示', { type: 'warning' })
  await returnsApi.remove(row.id)
  ElMessage.success('删除成功')
  await load()
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(() => {
  load()
  loadOptions()
})
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="请选择状态" style="width: 140px">
            <el-option label="待处理" value="待处理" />
            <el-option label="已完成" value="已完成" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button type="primary" data-test="btn-create" @click="openCreate">新增退货单</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="return_no" label="退货单号" width="180" />
      <el-table-column prop="sales_order_id" label="原订单 ID" width="110" />
      <el-table-column prop="return_date" label="退货日期" width="120" />
      <el-table-column prop="reason" label="原因" width="140" />
      <el-table-column label="金额" width="130">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.status]?.type || 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" :show-overflow-tooltip="false" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === '待处理'" link type="primary" data-test="btn-process" @click="onProcess(row)">处理入库</el-button>
          <el-button v-if="row.status === '待处理'" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSearch" />
  </el-card>

  <el-dialog v-model="dialogVisible" title="新增退货单" width="900px" destroy-on-close>
    <el-form :model="form" label-width="100px">
      <el-row>
        <el-col :span="12">
          <el-form-item label="原订单" required>
            <el-select v-model="form.sales_order_id" filterable placeholder="请选择原订单" data-test="field-sales_order_id" style="width: 100%">
              <el-option v-for="o in orders" :key="o.id" :label="o.order_no" :value="o.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="退货日期" required>
            <el-date-picker v-model="form.return_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="退货原因">
            <el-select v-model="form.reason" clearable placeholder="请选择原因" style="width: 100%">
              <el-option v-for="r in returnReasonOptions" :key="r.value" :label="r.label" :value="r.value" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="明细" required>
        <ItemsEditor
          v-model:rows="itemRows"
          :fields="[
            { prop: 'product_id', label: '商品', type: 'product' },
            { prop: 'quantity', label: '退货数量', type: 'quantity' },
            { prop: 'unit_price', label: '退货单价', type: 'price' },
            { prop: 'reason', label: '原因', type: 'text', placeholder: '行级原因' },
          ]"
          :product-options="products"
          @product-change="onProductChange"
        />
      </el-form-item>
      <el-form-item label="退货总额">
        <span class="total-text">￥{{ totalAmount().toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</span>
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
.total-text {
  font-size: 16px;
  font-weight: 600;
  color: #f56c6c;
}
</style>
