<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ option: Record<string, unknown>; height?: string }>()
const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (chart && props.option) {
    chart.setOption(props.option as echarts.EChartsOption)
  }
}

function resize() {
  chart?.resize()
}

onMounted(() => {
  if (!el.value) return
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', resize)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
})
</script>

<template>
  <div ref="el" class="chart" :style="{ height: props.height || '320px' }" />
</template>
