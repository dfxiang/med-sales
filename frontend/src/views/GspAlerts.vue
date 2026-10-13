<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { alertApi, type GspAlert, type GspAlertSummary } from '@/api/gsp'
import { alertLevelTagMap } from '@/utils/constants'

const router = useRouter()

const summary = ref<GspAlertSummary | null>(null)
const rows = ref<GspAlert[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
const category = ref<'all' | 'certificate' | 'batch'>('all')
const level = ref('all')

const categoryOptions = [
  { label: '全部', value: 'all' },
  { label: '证照', value: 'certificate' },
  { label: '批次', value: 'batch' },
]

const levelOptions = [
  { label: '全部', value: 'all' },
  { label: '已过期', value: '已过期' },
  { label: '30 天内', value: '30天内' },
  { label: '31-60 天', value: '60天内' },
  { label: '61-90 天', value: '90天内' },
]

const statCards = () => [
  { key: 'expired', label: '已过期', value: summary.value?.expired ?? 0, level: '已过期', type: 'danger' },
  { key: 'within_30', label: '30 天内到期', value: summary.value?.within_30 ?? 0, level: '30天内', type: 'danger' },
  { key: 'within_60', label: '31-60 天到期', value: summary.value?.within_60 ?? 0, level: '60天内', type: 'warning' },
  { key: 'within_90', label: '61-90 天到期', value: summary.value?.within_90 ?? 0, level: '90天内', type: 'warning' },
  { key: 'pending_review', label: '待审核资料', value: summary.value?.pending_review ?? 0, level: '', type: 'info' },
]

async function load() {
  loading.value = true
  try {
    const data = (await alertApi.list({
      category: category.value,
      level: level.value,
      page: page.value,
      size: size.value,
    })) as unknown as { items: GspAlert[]; total: number }
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function loadSummary() {
  summary.value = (await alertApi.summary()) as unknown as GspAlertSummary
}

function applyLevel(target: string) {
  if (target === '') {
    // 待审核资料：跳到证照台账按审核状态过滤
    router.push({ path: '/gsp/certificates' })
    return
  }
  level.value = target
  page.value = 1
  load()
}

function onFilterChange() {
  page.value = 1
  load()
}

function onSizeChange() {
  page.value = 1
  load()
}

function handleRow(row: GspAlert) {
  if (row.category === 'certificate') {
    router.push({
      path: '/gsp/qualification',
      query: { entity_type: row.entity_type ?? '', entity_id: row.entity_id ?? '' },
    })
  } else {
    router.push({ path: '/gsp/batches' })
  }
}

onMounted(async () => {
  await Promise.all([loadSummary(), load()])
})
</script>

<template>
  <div data-test="gsp-alerts">
    <div class="stat-row">
      <el-card
        v-for="card in statCards()"
        :key="card.key"
        class="stat-card"
        shadow="hover"
        :data-test="`alert-stat-${card.key}`"
        @click="applyLevel(card.level)"
      >
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value" :class="`text-${card.type}`">{{ card.value }}</div>
      </el-card>
    </div>

    <el-card>
      <div class="page-toolbar">
        <el-form :inline="true" class="search-form">
          <el-form-item label="预警类别">
            <el-select
              v-model="category"
              style="width: 140px"
              data-test="alert-category"
              @change="onFilterChange"
            >
              <el-option
                v-for="opt in categoryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="到期区间">
            <el-select
              v-model="level"
              style="width: 160px"
              data-test="alert-level"
              @change="onFilterChange"
            >
              <el-option
                v-for="opt in levelOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <el-table v-loading="loading" :data="rows" border stripe data-test="alert-table">
        <el-table-column label="类别" width="100">
          <template #default="{ row }">
            <el-tag :type="row.category === 'certificate' ? 'primary' : 'success'" size="small">
              {{ row.category === 'certificate' ? '证照' : '批次' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="对象" width="180" />
        <el-table-column prop="title" label="名称" min-width="180" />
        <el-table-column prop="valid_to" label="到期日期" width="130" />
        <el-table-column label="剩余天数" width="110">
          <template #default="{ row }">
            <span :class="row.days_left < 0 ? 'text-danger' : ''">
              {{ row.days_left < 0 ? `已过期 ${-row.days_left} 天` : `${row.days_left} 天` }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="110">
          <template #default="{ row }">
            <el-tag :type="alertLevelTagMap[row.level]?.type || 'info'">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" :show-overflow-tooltip="false" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" data-test="alert-goto" @click="handleRow(row)">
              {{ row.category === 'certificate' ? '查看档案' : '查看批次' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="load"
        @size-change="onSizeChange"
      />
    </el-card>
  </div>
</template>

<style scoped>
.stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  flex: 1 1 180px;
  cursor: pointer;
}
.stat-label {
  color: #909399;
  font-size: 13px;
}
.stat-value {
  font-size: 24px;
  font-weight: 600;
  margin-top: 8px;
}
.text-danger {
  color: #f56c6c;
}
.text-warning {
  color: #e6a23c;
}
.text-info {
  color: #909399;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
