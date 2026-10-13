<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { inventoryApi } from '@/api/inventory'
import ItemsEditor, { type ItemRow, type ProductOption } from '@/components/ItemsEditor.vue'
import { ensureEntityOptions } from '@/utils/catalogOptions'

const warehouses = ref<{ id: number; name: string }[]>([])
const products = ref<ProductOption[]>([])
const form = ref<Record<string, unknown>>({ movement_date: new Date().toISOString().slice(0, 10) })
const itemRows = ref<ItemRow[]>([{ quantity: 1 }])
const submitting = ref(false)

async function loadOptions() {
  const [wh, prod] = await Promise.all([
    ensureEntityOptions('warehouse'),
    ensureEntityOptions('product'),
  ])
  warehouses.value = wh as { id: number; name: string }[]
  products.value = prod as ProductOption[]
}

async function onSubmit() {
  if (!form.value.warehouse_id || !form.value.movement_date) {
    ElMessage.warning('请选择仓库和日期')
    return
  }
  if (!itemRows.value.length || itemRows.value.some((r) => !r.product_id || !r.quantity)) {
    ElMessage.warning('请填写至少一条完整明细')
    return
  }
  submitting.value = true
  try {
    await inventoryApi.openStock({
      warehouse_id: form.value.warehouse_id,
      movement_date: form.value.movement_date,
      items: itemRows.value.map((r) => ({ product_id: r.product_id, quantity: r.quantity })),
    })
    ElMessage.success('期初入库成功')
    itemRows.value = [{ quantity: 1 }]
    form.value = { movement_date: new Date().toISOString().slice(0, 10) }
  } finally {
    submitting.value = false
  }
}

onMounted(loadOptions)
</script>

<template>
  <el-card>
    <el-form :model="form" label-width="100px" style="max-width: 900px">
      <el-row>
        <el-col :span="12">
          <el-form-item label="仓库" required>
            <el-select v-model="form.warehouse_id" filterable placeholder="请选择仓库" data-test="field-warehouse_id" style="width: 100%">
              <el-option v-for="w in warehouses" :key="w.id" :label="w.name" :value="w.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="入库日期" required>
            <el-date-picker v-model="form.movement_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="明细" required>
        <ItemsEditor
          v-model:rows="itemRows"
          :fields="[
            { prop: 'product_id', label: '商品', type: 'product' },
            { prop: 'quantity', label: '期初数量', type: 'quantity' },
          ]"
          :product-options="products"
        />
      </el-form-item>
      <el-button v-permission="'inventory:manage'" type="primary" :loading="submitting" data-test="btn-submit" @click="onSubmit">提交入库</el-button>
    </el-form>
  </el-card>
</template>
