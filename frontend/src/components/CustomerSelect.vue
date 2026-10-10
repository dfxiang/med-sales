<script setup lang="ts">
import { onMounted } from 'vue'

import { useCustomerOptions } from '@/utils/customerOptions'

/**
 * 客户选择控件：下拉候选按名称模糊过滤，候选数据全站共用一份（见 utils/customerOptions）。
 *
 * 用法：<CustomerSelect v-model="form.customer_id" width="200px" data-test="filter-customer" />
 */
const props = withDefaults(
  defineProps<{
    modelValue?: number | null
    placeholder?: string
    width?: string
    clearable?: boolean
    disabled?: boolean
  }>(),
  {
    modelValue: null,
    placeholder: '请输入客户名称',
    width: '200px',
    clearable: true,
    disabled: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | undefined): void
  (e: 'change', value: number | undefined): void
}>()

const { options, loading, ensure } = useCustomerOptions()

function onChange(value: number | undefined) {
  emit('update:modelValue', value)
  emit('change', value)
}

onMounted(ensure)
</script>

<template>
  <el-select
    :model-value="props.modelValue ?? undefined"
    filterable
    :clearable="props.clearable"
    :disabled="props.disabled"
    :loading="loading"
    :placeholder="props.placeholder"
    :style="{ width: props.width }"
    @update:model-value="onChange"
  >
    <el-option v-for="c in options" :key="c.id" :label="c.name" :value="c.id" />
  </el-select>
</template>
