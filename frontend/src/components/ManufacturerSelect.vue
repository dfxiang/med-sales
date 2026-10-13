<script setup lang="ts">
import { useAttrs } from 'vue'

import EntitySelect from '@/components/EntitySelect.vue'

/**
 * 生产厂家选择控件（统一控件的薄封装，`v-model` 绑定厂家 ID）。
 *
 * 厂家表没有编码字段，候选只显示名称。
 */
defineOptions({ inheritAttrs: false })

const attrs = useAttrs()
</script>

<template>
  <EntitySelect
    entity="manufacturer"
    v-bind="attrs"
    :placeholder="(attrs.placeholder as string) || '请输入厂家名称'"
  />
</template>
