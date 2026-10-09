<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { productApi } from '@/api/product'
import { fetchAllOptions } from '@/utils/options'

interface PriceRow {
  id: number
  effective_date: string
  old_price: number | null
  new_price: number
  change_reason: string | null
  created_at: string
}

const products = ref<{ id: number; sku: string; name: string }[]>([])
const productId = ref<number | null>(null)
const rows = ref<PriceRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const dialogVisible = ref(false)
const saving = ref(false)
const form = ref({ effective_date: '', new_price: 0, change_reason: '' })

async function loadProducts() {
  products.value = await fetchAllOptions<{ id: number; sku: string; name: string }>('/products')
}

async function loadPrices() {
  if (productId.value === null) return
  const data = (await productApi.prices(productId.value, { page: page.value, size: size.value })) as { items: PriceRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSizeChange() {
  page.value = 1
  loadPrices()
}

function openAdjust() {
  if (productId.value === null) {
    ElMessage.warning('请先选择商品')
    return
  }
  form.value = { effective_date: new Date().toISOString().slice(0, 10), new_price: 0, change_reason: '' }
  dialogVisible.value = true
}

async function submitAdjust() {
  if (productId.value === null || !form.value.effective_date || form.value.new_price <= 0) {
    ElMessage.warning('请填写完整调价信息')
    return
  }
  saving.value = true
  try {
    await productApi.adjustPrice(productId.value, form.value)
    ElMessage.success('调价成功')
    dialogVisible.value = false
    await loadPrices()
  } finally {
    saving.value = false
  }
}

onMounted(loadProducts)
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
        <el-form-item label="商品">
          <el-select
            v-model="productId"
            filterable
            placeholder="请选择商品"
            data-test="product-select"
            style="width: 320px"
            @change="page = 1; loadPrices()"
          >
            <el-option v-for="p in products" :key="p.id" :label="`${p.sku} - ${p.name}`" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button v-permission="'product:manage'" type="primary" data-test="btn-adjust" @click="openAdjust">调价</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe data-test="price-table">
      <el-table-column prop="effective_date" label="生效日期" width="140" />
      <el-table-column label="调整前价格" width="140">
        <template #default="{ row }">{{ row.old_price === null ? '-' : Number(row.old_price).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column label="调整后价格" width="140">
        <template #default="{ row }">{{ Number(row.new_price).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}</template>
      </el-table-column>
      <el-table-column prop="change_reason" label="调价原因" min-width="180" />
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ String(row.created_at).replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="loadPrices" @size-change="onSizeChange" />
  </el-card>

  <el-dialog v-model="dialogVisible" title="价格调整" width="480px">
    <el-form :model="form" label-width="100px">
      <el-form-item label="生效日期" required>
        <el-date-picker v-model="form.effective_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" data-test="field-effective_date" />
      </el-form-item>
      <el-form-item label="新价格" required>
        <el-input-number v-model="form.new_price" :min="0" :precision="2" style="width: 100%" />
      </el-form-item>
      <el-form-item label="调价原因">
        <el-input v-model="form.change_reason" placeholder="如：挂网价调整" data-test="field-change_reason" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" data-test="btn-save" @click="submitAdjust">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
