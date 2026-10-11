<script setup lang="ts">
import { useAttrs } from 'vue'

import EntitySelect from '@/components/EntitySelect.vue'

/**
 * 员工（销售员）选择控件（统一控件的薄封装，`v-model` 绑定员工 ID）。
 *
 * 候选显示「工号 - 姓名」（与商品的「SKU - 名称」同一个格式），输入工号或姓名片段都能命中。
 */
defineOptions({ inheritAttrs: false })

const attrs = useAttrs()
</script>

<template>
  <EntitySelect
    entity="employee"
    v-bind="attrs"
    :placeholder="(attrs.placeholder as string) || '请输入工号/姓名'"
  />
</template>
