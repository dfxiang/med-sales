<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { auditLogApi } from '@/api/system'

interface LogRow {
  id: number
  username: string | null
  action: string
  module: string
  detail: string | null
  created_at: string
}

const rows = ref<LogRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const username = ref('')
const module = ref('')

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (username.value) params.username = username.value
  if (module.value) params.module = module.value
  const data = (await auditLogApi.list(params)) as { items: LogRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSizeChange() {
  page.value = 1
  load()
}

onMounted(load)
</script>

<template>
  <el-card>
    <el-form inline>
      <el-form-item label="用户名">
        <el-input v-model="username" placeholder="请输入用户名" clearable style="width: 160px" @keyup.enter="page = 1; load()" />
      </el-form-item>
      <el-form-item label="模块">
        <el-input v-model="module" placeholder="请输入模块" clearable style="width: 160px" @keyup.enter="page = 1; load()" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" data-test="btn-search" @click="page = 1; load()">查询</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="rows" border stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="module" label="模块" width="120" />
      <el-table-column prop="action" label="操作" width="120" />
      <el-table-column prop="detail" label="详情" min-width="220" />
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ String(row.created_at).replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSizeChange" />
  </el-card>
</template>

<style scoped>
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
