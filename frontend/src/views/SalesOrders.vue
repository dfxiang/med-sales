<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { salesApi } from '@/api/sales'
import CustomerSelect from '@/components/CustomerSelect.vue'
import EmployeeSelect from '@/components/EmployeeSelect.vue'
import ItemsEditor, { type ItemRow, type ProductOption } from '@/components/ItemsEditor.vue'
import WarehouseSelect from '@/components/WarehouseSelect.vue'
import { useUserStore } from '@/stores/user'
import { fetchAllOptions } from '@/utils/options'
import {
  deliveryTypeOptions,
  invoiceTypeOptions,
  settlementOptions,
  statusTagMap,
} from '@/utils/constants'

interface OrderRow {
  id: number
  order_no: string
  customer_id: number
  customer_name: string | null
  employee_id: number
  employee_name: string | null
  warehouse_id: number
  order_date: string
  status: string
  total_amount: number
  paid_amount: number
}

const rows = ref<OrderRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filters = ref<Record<string, unknown>>({})

// 开单弹窗的金额预览需要商品挂网价。候选接口只给「编码 / 名称」，价格仍属于商品档案，
// 因此这里按 product:view 权限**懒加载**（打开弹窗时才拉，且无权限就不发请求），
// 金额本身以服务端下单结果为准。
const productPrices = ref<Record<number, number>>({})
const userStore = useUserStore()

async function ensureProductPrices() {
  if (Object.keys(productPrices.value).length) return
  if (!userStore.hasPermission('product:view')) return
  const list = await fetchAllOptions<{ id: number; standard_price: number }>('/products')
  productPrices.value = Object.fromEntries(
    list.map((item) => [item.id, Number(item.standard_price ?? 0)]),
  )
}

const dialogVisible = ref(false)
const saving = ref(false)
const form = ref<Record<string, unknown>>({})
const itemRows = ref<ItemRow[]>([])

const shipVisible = ref(false)
const shipping = ref(false)
const currentOrder = ref<OrderRow | null>(null)
const shipDate = ref(new Date().toISOString().slice(0, 10))

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value, ...filters.value }
  // 订单号支持输入片段；空串不参与筛选
  const orderNo = String(filters.value.order_no ?? '').trim()
  if (orderNo) params.order_no = orderNo
  else delete params.order_no
  const data = (await salesApi.list(params)) as { items: OrderRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function openCreate() {
  form.value = {
    order_date: new Date().toISOString().slice(0, 10),
    invoice_type: '增值税专用发票',
    settlement_method: '现款',
    delivery_type: '常温运输',
  }
  itemRows.value = [{ quantity: 1, discount_rate: 0 }]
  dialogVisible.value = true
}

async function onProductChange(row: ItemRow, product: ProductOption) {
  await ensureProductPrices()
  row.unit_price = productPrices.value[product.id] ?? 0
}

function totals() {
  const subtotal = itemRows.value.reduce(
    (sum, r) => sum + Number(r.unit_price || 0) * Number(r.quantity || 0),
    0,
  )
  const discount = itemRows.value.reduce(
    (sum, r) => sum + Number(r.unit_price || 0) * Number(r.quantity || 0) * Number(r.discount_rate || 0),
    0,
  )
  return { subtotal, discount, total: subtotal - discount }
}

async function onSubmit() {
  if (!form.value.customer_id || !form.value.employee_id || !form.value.warehouse_id || !form.value.order_date) {
    ElMessage.warning('请填写客户、销售员、仓库和下单日期')
    return
  }
  if (!itemRows.value.length || itemRows.value.some((r) => !r.product_id || !r.quantity)) {
    ElMessage.warning('请填写至少一条完整明细')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form.value,
      items: itemRows.value.map((r) => ({
        product_id: r.product_id,
        quantity: r.quantity,
        discount_rate: r.discount_rate || 0,
      })),
    }
    await salesApi.create(payload)
    ElMessage.success('销售订单创建成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

function openShip(order: OrderRow) {
  currentOrder.value = order
  shipDate.value = new Date().toISOString().slice(0, 10)
  shipVisible.value = true
}

async function submitShip() {
  if (!currentOrder.value) return
  shipping.value = true
  try {
    await salesApi.ship(currentOrder.value.id, shipDate.value)
    ElMessage.success('发货成功')
    shipVisible.value = false
    await load()
  } finally {
    shipping.value = false
  }
}

async function onCancel(order: OrderRow) {
  await ElMessageBox.confirm(`确定取消订单 ${order.order_no} 吗？`, '提示', { type: 'warning' })
  await salesApi.cancel(order.id)
  ElMessage.success('订单已取消')
  await load()
}

async function onDelete(order: OrderRow) {
  await ElMessageBox.confirm('确定删除该订单吗？', '提示', { type: 'warning' })
  await salesApi.remove(order.id)
  ElMessage.success('删除成功')
  await load()
}

function onSearch() {
  page.value = 1
  load()
}

onMounted(() => {
  load()
})
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
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="请选择状态" style="width: 140px">
            <el-option v-for="s in ['待付款', '已发货', '已完成', '已取消']" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="客户">
          <CustomerSelect v-model="filters.customer_id" width="200px" data-test="filter-customer" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button v-permission="'sales:manage'" type="primary" data-test="btn-create" @click="openCreate">新增销售单</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="order_no" label="订单号" width="180" />
      <!-- 客户名称较长（实测最长 206px），宽度给足避免一进入就被省略号截断 -->
      <el-table-column label="客户" width="360">
        <template #default="{ row }">{{ row.customer_name || row.customer_id }}</template>
      </el-table-column>
      <el-table-column label="销售员" width="110">
        <template #default="{ row }">{{ row.employee_name || row.employee_id }}</template>
      </el-table-column>
      <el-table-column prop="order_date" label="下单日期" width="120" />
      <el-table-column label="应收" width="130">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString($intlLocale(), { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="已收" width="130">
        <template #default="{ row }">{{ Number(row.paid_amount).toLocaleString($intlLocale(), { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.status]?.type || 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" :show-overflow-tooltip="false" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="!row.delivery_date && row.status !== '已取消' && row.status !== '已完成'" v-permission="'sales:manage'" link type="primary" data-test="btn-ship" @click="openShip(row)">发货</el-button>
          <el-button v-if="!row.delivery_date && row.status !== '已取消' && row.status !== '已完成'" v-permission="'sales:manage'" link type="warning" data-test="btn-cancel" @click="onCancel(row)">取消</el-button>
          <el-button v-if="row.status === '待付款' && !row.delivery_date" v-permission="'sales:manage'" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSearch" />
  </el-card>

  <el-dialog v-model="dialogVisible" title="新增销售订单" width="1000px" destroy-on-close>
    <el-form :model="form" label-width="100px">
      <el-row>
        <el-col :span="8">
          <el-form-item label="客户" required>
            <CustomerSelect
              v-model="form.customer_id"
              :clearable="false"
              placeholder="请选择客户"
              width="100%"
              data-test="field-customer_id"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="销售员" required>
            <EmployeeSelect
              v-model="form.employee_id"
              data-test="field-employee_id"
              width="100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="发货仓库" required>
            <WarehouseSelect
              v-model="form.warehouse_id"
              data-test="field-warehouse_id"
              width="100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="下单日期" required>
            <el-date-picker v-model="form.order_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="结算方式">
            <el-select v-model="form.settlement_method" style="width: 100%">
              <el-option v-for="s in settlementOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="开票类型">
            <el-select v-model="form.invoice_type" style="width: 100%">
              <el-option v-for="s in invoiceTypeOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="配送方式">
            <el-select v-model="form.delivery_type" style="width: 100%">
              <el-option v-for="s in deliveryTypeOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="收货地址">
            <el-input v-model="form.shipping_address" placeholder="请输入收货地址" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="明细" required>
        <ItemsEditor
          v-model:rows="itemRows"
          :fields="[
            { prop: 'product_id', label: '商品', type: 'product' },
            { prop: 'quantity', label: '数量', type: 'quantity' },
            { prop: 'discount_rate', label: '折扣率', type: 'rate' },
          ]"
          @product-change="onProductChange"
        />
      </el-form-item>
      <el-form-item label="金额汇总">
        <span v-if="Object.keys(productPrices).length" class="total-text">
          小计 ￥{{ totals().subtotal.toFixed(2) }}　优惠 ￥{{ totals().discount.toFixed(2) }}　应收 ￥{{ totals().total.toFixed(2) }}
        </span>
        <span v-else class="total-text">当前账号无「查看商品」权限，金额以下单结果为准</span>
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

  <el-dialog v-model="shipVisible" title="销售发货" width="420px">
    <el-form label-width="90px">
      <el-form-item label="发货日期" required>
        <el-date-picker v-model="shipDate" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="订单">
        <span>{{ currentOrder?.order_no }}</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="shipVisible = false">取消</el-button>
      <el-button type="primary" :loading="shipping" data-test="btn-ship-save" @click="submitShip">确认发货</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
.total-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-color-danger);
}
</style>
