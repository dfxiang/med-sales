<script setup lang="ts">
import { useAttrs } from 'vue'

import EntitySelect from '@/components/EntitySelect.vue'

/**
 * 客户选择控件（统一控件的薄封装，`v-model` 绑定客户 ID）。
 *
 * 客户有上千条，候选走服务端关键词搜索，输入名称或编码片段即可命中。
 */
defineOptions({ inheritAttrs: false })

const attrs = useAttrs()
</script>

<template>
  <EntitySelect
    entity="customer"
    v-bind="attrs"
    :placeholder="(attrs.placeholder as string) || '请输入客户名称/编码'"
  />
</template>
