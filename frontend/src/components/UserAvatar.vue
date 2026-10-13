<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { avatarSrc } from '@/utils/avatar'

/**
 * 统一头像控件：图片加载失败时回落到内置默认头像。
 *
 * 为什么需要兜底：`avatar_url` 只保证"数据库里有对象键"，并不保证对象存储里
 * 一定有对应对象（对象被清理、上传中断、换存储后未迁移等）。这种情况浏览器拿到
 * 404，`el-avatar` 会退化成"灰底 + 首字"，看起来就是"明明有头像却没有图像"。
 * 这里改成回落到默认头像，任何情况下都显示一张图；只有连默认头像都取不到时，
 * 才显示首字。
 */
const props = withDefaults(
  defineProps<{
    /** 已经拼装好的头像地址（含本地预览的 blob 地址） */
    src?: string | null
    size?: number
    /** 首字兜底用的名称（仅在默认头像也加载失败时才会用到） */
    name?: string | null
  }>(),
  { size: 32 },
)

const failed = ref(false)

// 头像地址变化（例如用户刚换完头像）后重新尝试加载，避免一直被失败状态锁定
watch(
  () => props.src,
  () => {
    failed.value = false
  },
)

const resolvedSrc = computed(() => (failed.value ? avatarSrc(null) : props.src || avatarSrc(null)))
const initial = computed(() => (props.name || '').trim().slice(0, 1))
</script>

<template>
  <el-avatar :size="size" :src="resolvedSrc" @error="failed = true">
    <span>{{ initial }}</span>
  </el-avatar>
</template>
