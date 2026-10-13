<script setup lang="ts">
import { useAttrs } from 'vue'

import EntitySelect from '@/components/EntitySelect.vue'

/** 商品选择控件（统一控件的薄封装，`v-model` 绑定商品 ID）。候选显示「SKU - 名称」。 */
defineOptions({ inheritAttrs: false })

const attrs = useAttrs()
</script>

<template>
  <EntitySelect
    entity="product"
    v-bind="attrs"
    :placeholder="(attrs.placeholder as string) || '请输入商品名称/SKU'"
  />
</template>
