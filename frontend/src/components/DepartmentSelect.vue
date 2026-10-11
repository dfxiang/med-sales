<script setup lang="ts">
import { useAttrs } from 'vue'

import EntitySelect from '@/components/EntitySelect.vue'

/** 部门选择控件（统一控件的薄封装，`v-model` 绑定部门 ID）。候选显示「编码 - 名称」。 */
defineOptions({ inheritAttrs: false })

const attrs = useAttrs()
</script>

<template>
  <EntitySelect
    entity="department"
    v-bind="attrs"
    :placeholder="(attrs.placeholder as string) || '请输入部门名称/编码'"
  />
</template>
