<script setup lang="ts">
import { ElMessage } from 'element-plus'

export interface ItemField {
  prop: string
  label: string
  type: 'product' | 'quantity' | 'price' | 'rate' | 'text'
  placeholder?: string
}

export interface ItemRow {
  product_id?: number
  quantity?: number
  unit_cost?: number
  unit_price?: number
  discount_rate?: number
  reason?: string
  [key: string]: unknown
}

export interface ProductOption {
  id: number
  sku: string
  name: string
  standard_price?: number
  cost_price?: number
}

const props = defineProps<{
  fields: ItemField[]
  productOptions: ProductOption[]
  rows: ItemRow[]
}>()

const emit = defineEmits<{
  (e: 'update:rows', rows: ItemRow[]): void
  (e: 'product-change', row: ItemRow, product: ProductOption): void
}>()

function addRow() {
  emit('update:rows', [...props.rows, { quantity: 1 }])
}

function removeRow(index: number) {
  const rows = [...props.rows]
  rows.splice(index, 1)
  emit('update:rows', rows)
}

function onProductChange(row: ItemRow, productId: number) {
  const product = props.productOptions.find((p) => p.id === productId)
  if (!product) {
    ElMessage.warning('请选择商品')
    return
  }
  emit('product-change', row, product)
}
</script>

<template>
  <div>
    <el-table :data="rows" border size="small" class="items-table" data-test="items-table">
      <el-table-column label="#" width="50">
        <template #default="{ $index }">{{ $index + 1 }}</template>
      </el-table-column>
      <el-table-column v-for="field in fields" :key="field.prop" :label="field.label" min-width="170">
        <template #default="{ row }">
          <el-select
            v-if="field.type === 'product'"
            v-model="row.product_id"
            filterable
            placeholder="请选择商品"
            style="width: 100%"
            @change="(v: number) => onProductChange(row, v)"
          >
            <el-option
              v-for="p in productOptions"
              :key="p.id"
              :label="`${p.sku} - ${p.name}`"
              :value="p.id"
            />
          </el-select>
          <el-input-number
            v-else-if="field.type === 'quantity'"
            v-model="row.quantity"
            :min="1"
            :controls="false"
            style="width: 100%"
          />
          <el-input-number
            v-else-if="field.type === 'price'"
            v-model="row[field.prop]"
            :min="0"
            :precision="2"
            :controls="false"
            style="width: 100%"
          />
          <el-input-number
            v-else-if="field.type === 'rate'"
            v-model="row.discount_rate"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="2"
            style="width: 100%"
          />
          <el-input
            v-else-if="field.type === 'text'"
            v-model="row[field.prop]"
            :placeholder="field.placeholder || '请输入'"
            style="width: 100%"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" fixed="right">
        <template #default="{ $index }">
          <el-button link type="danger" data-test="btn-remove-item" @click="removeRow($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-button type="primary" plain data-test="btn-add-item" class="add-item-btn" @click="addRow">
      添加明细
    </el-button>
  </div>
</template>

<style scoped>
.items-table {
  margin-bottom: 8px;
}
.add-item-btn {
  margin-bottom: 4px;
}
</style>
