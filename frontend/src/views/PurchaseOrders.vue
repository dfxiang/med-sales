<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { purchaseApi } from '@/api/purchase'
import SupplierSelect from '@/components/SupplierSelect.vue'
import WarehouseSelect from '@/components/WarehouseSelect.vue'
import ItemsEditor, { type ItemRow, type ProductOption } from '@/components/ItemsEditor.vue'
import { useUserStore } from '@/stores/user'
import { statusTagMap } from '@/utils/constants'
import { fetchAllOptions } from '@/utils/options'

interface OrderRow {
  id: number
  order_no: string
  supplier_id: number
  warehouse_id: number
  order_date: string
  status: string
  total_amount: number
  supplier_name?: string | null
  warehouse_name?: string | null
  items: {
    id: number
    product_id: number
    quantity: number
    unit_cost: number
    received_quantity: number
    product?: { sku?: string | null; name: string } | null
  }[]
}

const rows = ref<OrderRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filters = ref<Record<string, unknown>>({})

// 采购明细的单价默认取商品成本价。候选接口只给「编码 / 名称」，成本价属于商品档案，
// 因此按 product:view 权限懒加载（无权限时不发请求，单价留空由采购员自己填）。
const productCosts = ref<Record<number, number>>({})
const userStore = useUserStore()

async function ensureProductCosts() {
  if (Object.keys(productCosts.value).length) return
  if (!userStore.hasPermission('product:view')) return
  const list = await fetchAllOptions<{ id: number; cost_price: number }>('/products')
  productCosts.value = Object.fromEntries(
    list.map((item) => [item.id, Number(item.cost_price ?? 0)]),
  )
}

const dialogVisible = ref(false)
const saving = ref(false)
const form = ref<Record<string, unknown>>({})
const itemRows = ref<ItemRow[]>([])

const receiveVisible = ref(false)
const receiving = ref(false)
const currentOrder = ref<OrderRow | null>(null)
const receiveRows = ref<{ item_id: number; product_name: string; ordered: number; received: number; qty: number }[]>([])

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value, ...filters.value }
  // 采购单号支持输入片段；空串不参与筛选
  const orderNo = String(filters.value.order_no ?? '').trim()
  if (orderNo) params.order_no = orderNo
  else delete params.order_no
  const data = (await purchaseApi.list(params)) as { items: OrderRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function openCreate() {
  form.value = {
    order_date: new Date().toISOString().slice(0, 10),
    expected_date: '',
    delivery_type: '常温运输',
  }
  itemRows.value = [{ quantity: 1 }]
  dialogVisible.value = true
}

async function onProductChange(row: ItemRow, product: ProductOption) {
  if (row.unit_cost === undefined || row.unit_cost === null || row.unit_cost === 0) {
    await ensureProductCosts()
    row.unit_cost = productCosts.value[product.id] ?? 0
  }
}

function totalAmount(): number {
  return itemRows.value.reduce((sum, r) => sum + Number(r.unit_cost || 0) * Number(r.quantity || 0), 0)
}

async function onSubmit() {
  if (!form.value.supplier_id || !form.value.warehouse_id || !form.value.order_date) {
    ElMessage.warning('请填写供应商、仓库和下单日期')
    return
  }
  if (!itemRows.value.length || itemRows.value.some((r) => !r.product_id || !r.quantity)) {
    ElMessage.warning('请填写至少一条完整明细')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form.value }
    for (const key of Object.keys(payload)) {
      if (payload[key] === '' || payload[key] === undefined) {
        delete payload[key]
      }
    }
    Object.assign(payload, {
      items: itemRows.value.map((r) => ({
        product_id: r.product_id,
        quantity: r.quantity,
        unit_cost: r.unit_cost,
      })),
    })
    await purchaseApi.create(payload)
    ElMessage.success('采购单创建成功')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

function openReceive(order: OrderRow) {
  currentOrder.value = order
  receiveRows.value = order.items.map((item) => ({
    item_id: item.id,
    product_name: productLabel(item),
    ordered: item.quantity,
    received: item.received_quantity,
    qty: Math.max(item.quantity - item.received_quantity, 0),
  }))
  receiveVisible.value = true
}

/** 收货弹窗里的商品名：优先用后端返回的 SKU + 名称。 */
function productLabel(item: OrderRow['items'][number]): string {
  const product = item.product
  if (!product) return `#${item.product_id}`
  return product.sku ? `${product.sku} - ${product.name}` : product.name
}

async function submitReceive() {
  if (!currentOrder.value) return
  const items = receiveRows.value.filter((r) => r.qty > 0).map((r) => ({ item_id: r.item_id, received_quantity: r.qty }))
  if (!items.length) {
    ElMessage.warning('请填写收货数量')
    return
  }
  receiving.value = true
  try {
    await purchaseApi.receive(currentOrder.value.id, {
      received_date: new Date().toISOString().slice(0, 10),
      items,
    })
    ElMessage.success('收货成功')
    receiveVisible.value = false
    await load()
  } finally {
    receiving.value = false
  }
}

async function onDelete(order: OrderRow) {
  await ElMessageBox.confirm('确定删除该采购单吗？', '提示', { type: 'warning' })
  await purchaseApi.remove(order.id)
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
        <el-form-item label="采购单号">
          <el-input
            v-model="filters.order_no"
            clearable
            placeholder="请输入采购单号"
            data-test="filter-order-no"
            style="width: 200px"
            @keyup.enter="onSearch"
            @clear="onSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="请选择状态" style="width: 150px">
            <el-option label="待收货" value="待收货" />
            <el-option label="部分收货" value="部分收货" />
            <el-option label="已完成" value="已完成" />
          </el-select>
        </el-form-item>
        <el-form-item label="供应商">
          <SupplierSelect v-model="filters.supplier_id" width="200px" data-test="filter-supplier" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button v-permission="'purchase:manage'" type="primary" data-test="btn-create" @click="openCreate">新增采购单</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="order_no" label="采购单号" width="180" />
      <el-table-column label="供应商" width="300">
        <template #default="{ row }">{{ row.supplier_name || row.supplier_id }}</template>
      </el-table-column>
      <el-table-column label="仓库" width="150">
        <template #default="{ row }">{{ row.warehouse_name || row.warehouse_id }}</template>
      </el-table-column>
      <el-table-column prop="order_date" label="下单日期" width="120" />
      <el-table-column label="金额" width="130">
        <template #default="{ row }">{{ Number(row.total_amount).toLocaleString($intlLocale(), { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTagMap[row.status]?.type || 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" :show-overflow-tooltip="false" width="180" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status !== '已完成'" v-permission="'purchase:manage'" link type="primary" data-test="btn-receive" @click="openReceive(row)">收货</el-button>
          <el-button v-if="row.status === '待收货'" v-permission="'purchase:manage'" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSearch" />
  </el-card>

  <el-dialog v-model="dialogVisible" title="新增采购单" width="900px" destroy-on-close>
    <el-form :model="form" label-width="90px">
      <el-row>
        <el-col :span="12">
          <el-form-item label="供应商" required>
            <SupplierSelect v-model="form.supplier_id" width="100%" data-test="field-supplier_id" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="收货仓库" required>
            <WarehouseSelect v-model="form.warehouse_id" width="100%" data-test="field-warehouse_id" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="下单日期" required>
            <el-date-picker v-model="form.order_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="预计到货">
            <el-date-picker v-model="form.expected_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="运输方式">
            <el-select v-model="form.delivery_type" style="width: 100%">
              <el-option label="常温运输" value="常温运输" />
              <el-option label="冷链运输" value="冷链运输" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="明细" required>
        <ItemsEditor
          v-model:rows="itemRows"
          :fields="[
            { prop: 'product_id', label: '商品', type: 'product' },
            { prop: 'quantity', label: '采购数量', type: 'quantity' },
            { prop: 'unit_cost', label: '采购单价', type: 'price' },
          ]"
          @product-change="onProductChange"
        />
      </el-form-item>
      <el-form-item label="采购总额">
        <span class="total-text">￥{{ totalAmount().toLocaleString($intlLocale(), { minimumFractionDigits: 2 }) }}</span>
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

  <el-dialog v-model="receiveVisible" title="采购收货" width="640px">
    <el-table :data="receiveRows" border size="small">
      <el-table-column prop="product_name" label="商品" min-width="160" />
      <el-table-column prop="ordered" label="采购数量" width="100" />
      <el-table-column prop="received" label="已收" width="100" />
      <el-table-column label="本次实收" width="150">
        <template #default="{ row }">
          <el-input-number v-model="row.qty" :min="0" :max="row.ordered - row.received" :controls="false" style="width: 100%" />
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <el-button @click="receiveVisible = false">取消</el-button>
      <el-button type="primary" :loading="receiving" data-test="btn-receive-save" @click="submitReceive">确认收货</el-button>
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
  color: var(--el-color-danger);
}
</style>
