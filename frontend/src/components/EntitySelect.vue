<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import {
  ensureEntityOptions,
  entityConfig,
  entityLabel,
  getEntityOption,
  searchEntityOptions,
  type CatalogOption,
  type EntityKey,
} from '@/utils/catalogOptions'

/**
 * 统一业务对象选择控件（客户 / 商品 / 分类 / 厂家 / 供应商 / 仓库）。
 *
 * - 候选显示「编码 - 名称」（商品的编码是 SKU，厂家没有编码则只显示名称）；
 * - 小数据量对象首屏拉全量并全站缓存，本地匹配，输入编码或名称片段都能命中；
 * - 大数据量对象（客户）走服务端关键词搜索，编辑态按主键回填显示文本；
 * - 页面一律用本控件或它的薄封装（ProductSelect / SupplierSelect ...），不要再自建
 *   `el-select` + `fetchAllOptions()`。
 *
 * 用法：`<EntitySelect entity="product" v-model="form.product_id" width="100%" />`
 */
const props = withDefaults(
  defineProps<{
    entity: EntityKey
    modelValue?: number | null
    placeholder?: string
    width?: string
    clearable?: boolean
    disabled?: boolean
  }>(),
  {
    modelValue: null,
    placeholder: '',
    width: '220px',
    clearable: true,
    disabled: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | undefined): void
  (e: 'change', value: number | undefined, option: CatalogOption | null): void
}>()

const config = computed(() => entityConfig(props.entity))
const isRemote = computed(() => config.value.remote)
const placeholder = computed(() => props.placeholder || `请选择${config.value.label}`)

const options = ref<CatalogOption[]>([])
const loading = ref(false)

function labelOf(option: CatalogOption): string {
  return entityLabel(props.entity, option as unknown as Record<string, unknown>)
}

/** 已选值必须始终在候选里，否则编辑态会显示成空白。 */
async function backfillCurrent() {
  const id = props.modelValue
  if (id === null || id === undefined) return
  if (options.value.some((item) => item.id === id)) return
  const option = await getEntityOption(props.entity, id)
  if (option && props.modelValue === id) options.value = [option, ...options.value]
}

/** 小数据量对象：拉全量（有缓存则直接复用）。 */
async function loadAll() {
  if (isRemote.value) return
  loading.value = true
  try {
    options.value = await ensureEntityOptions(props.entity)
  } finally {
    loading.value = false
  }
}

/** 大数据量对象：按关键词远程搜索；空关键词时给一页候选，保证点开就有内容。 */
async function search(keyword: string) {
  if (!isRemote.value) return
  loading.value = true
  try {
    const list = await searchEntityOptions(props.entity, keyword)
    const current = options.value.find((item) => item.id === props.modelValue)
    options.value = current && !list.some((item) => item.id === current.id) ? [current, ...list] : list
  } finally {
    loading.value = false
  }
}

async function reload() {
  options.value = []
  if (isRemote.value) {
    await search('')
  } else {
    await loadAll()
  }
  await backfillCurrent()
}

watch(() => props.entity, reload)
watch(() => props.modelValue, backfillCurrent)

onMounted(reload)

function onChange(value: number | undefined) {
  const option = options.value.find((item) => item.id === value) ?? null
  emit('update:modelValue', value)
  emit('change', value, option)
}
</script>

<template>
  <el-select
    :model-value="props.modelValue ?? undefined"
    filterable
    :remote="isRemote"
    :reserve-keyword="isRemote"
    :remote-method="isRemote ? search : undefined"
    :clearable="props.clearable"
    :disabled="props.disabled"
    :loading="loading"
    :placeholder="placeholder"
    :style="{ width: props.width }"
    @update:model-value="onChange"
  >
    <el-option v-for="option in options" :key="option.id" :label="labelOf(option)" :value="option.id" />
  </el-select>
</template>
