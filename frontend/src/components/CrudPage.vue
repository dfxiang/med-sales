<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export interface Column {
  prop: string
  label: string
  width?: number | string
  type?: 'text' | 'money' | 'date' | 'datetime' | 'tag'
  tagMap?: Record<string, { text?: string; type?: 'success' | 'warning' | 'danger' | 'info' | 'primary' }>
}

export interface SearchField {
  prop: string
  label: string
  type?: 'input' | 'select'
  options?: { label: string; value: string | number }[]
  placeholder?: string
}

export interface FormField {
  prop: string
  label: string
  type: 'input' | 'number' | 'textarea' | 'select' | 'date' | 'switch'
  required?: boolean
  options?: { label: string; value: string | number | boolean }[]
  optionsApi?: () => Promise<Record<string, unknown>[]>
  optionLabel?: string
  optionValue?: string
  placeholder?: string
  default?: unknown
  span?: number
  nullable?: boolean
}

export interface CrudApi {
  list: (params: Record<string, unknown>) => Promise<{ items: Record<string, unknown>[]; total: number }>
  create?: (data: Record<string, unknown>) => Promise<unknown>
  update?: (id: number | string, data: Record<string, unknown>) => Promise<unknown>
  remove?: (id: number | string) => Promise<unknown>
}

const props = defineProps<{
  title: string
  api: CrudApi
  columns: Column[]
  searchFields?: SearchField[]
  formFields?: FormField[]
  rowKey?: string
}>()

const rows = ref<Record<string, unknown>[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
const searchForm = reactive<Record<string, unknown>>({})
const dialogVisible = ref(false)
const editingId = ref<number | string | null>(null)
const saving = ref(false)
const form = reactive<Record<string, unknown>>({})

const hasCreate = computed(() => !!props.api.create)
const hasUpdate = computed(() => !!props.api.update)
const hasRemove = computed(() => !!props.api.remove)

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, size: size.value }
    for (const field of props.searchFields || []) {
      if (searchForm[field.prop] !== '' && searchForm[field.prop] !== undefined && searchForm[field.prop] !== null) {
        params[field.prop] = searchForm[field.prop]
      }
    }
    const data = await props.api.list(params)
    rows.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  for (const key of Object.keys(form)) delete form[key]
  for (const field of props.formFields || []) {
    form[field.prop] =
      field.default ??
      (field.type === 'switch' ? false : field.type === 'number' ? (field.nullable ? '' : 0) : '')
  }
  loadFieldOptions()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>) {
  editingId.value = (row as Record<string, unknown>)[props.rowKey || 'id'] as number | string
  for (const key of Object.keys(form)) delete form[key]
  for (const field of props.formFields || []) {
    form[field.prop] = row[field.prop] ?? field.default ?? ''
  }
  loadFieldOptions()
  dialogVisible.value = true
}

async function loadFieldOptions() {
  for (const field of props.formFields || []) {
    if (field.optionsApi) {
      try {
        const data = await field.optionsApi()
        field.options = data.map((item) => ({
          label: String(item[field.optionLabel || 'name']),
          value: item[field.optionValue || 'id'] as string | number | boolean,
        }))
      } catch {
        field.options = []
      }
    }
  }
}

async function onSubmit() {
  for (const field of props.formFields || []) {
    if (field.required && (form[field.prop] === '' || form[field.prop] === undefined || form[field.prop] === null)) {
      ElMessage.warning(`请填写${field.label}`)
      return
    }
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form }
    for (const field of props.formFields || []) {
      if (!field.required && (payload[field.prop] === '' || payload[field.prop] === null)) {
        delete payload[field.prop]
      }
    }
    if (editingId.value !== null && props.api.update) {
      await props.api.update(editingId.value, payload)
      ElMessage.success('更新成功')
    } else if (props.api.create) {
      await props.api.create(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: Record<string, unknown>) {
  if (!props.api.remove) return
  await ElMessageBox.confirm('确定删除该记录吗？', '提示', { type: 'warning' })
  await props.api.remove((row as Record<string, unknown>)[props.rowKey || 'id'] as number)
  ElMessage.success('删除成功')
  await load()
}

function onSearch() {
  page.value = 1
  load()
}

function onReset() {
  for (const key of Object.keys(searchForm)) delete searchForm[key]
  page.value = 1
  load()
}

function cellText(row: Record<string, unknown>, column: Column): string {
  const value = row[column.prop]
  if (value === null || value === undefined) return ''
  if (column.type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
  if (column.type === 'date') return String(value).slice(0, 10)
  if (column.type === 'datetime') return String(value).replace('T', ' ').slice(0, 19)
  return String(value)
}

onMounted(load)
</script>

<template>
  <div data-test="crud-page">
    <el-card>
      <div class="page-toolbar">
        <el-form v-if="searchFields?.length" :inline="true" class="search-form">
          <el-form-item v-for="field in searchFields" :key="field.prop" :label="field.label">
            <el-select
              v-if="field.type === 'select'"
              v-model="searchForm[field.prop]"
              clearable
              :placeholder="field.placeholder || `请选择${field.label}`"
              :data-test="`search-${field.prop}`"
              style="width: 180px"
            >
              <el-option v-for="opt in field.options" :key="String(opt.value)" :label="opt.label" :value="opt.value" />
            </el-select>
            <el-input
              v-else
              v-model="searchForm[field.prop]"
              :placeholder="field.placeholder || `请输入${field.label}`"
              :data-test="`search-${field.prop}`"
              clearable
              style="width: 180px"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" data-test="btn-search" @click="onSearch">查询</el-button>
            <el-button data-test="btn-reset" @click="onReset">重置</el-button>
          </el-form-item>
        </el-form>
        <div class="page-toolbar-actions">
          <el-button v-if="hasCreate" type="primary" data-test="btn-create" @click="openCreate">
            新增
          </el-button>
        </div>
      </div>

      <el-table :data="rows" v-loading="loading" border stripe data-test="table">
        <el-table-column
          v-for="column in columns"
          :key="column.prop"
          :prop="column.prop"
          :label="column.label"
          :width="column.width"
        >
          <template #default="{ row }">
            <el-tag v-if="column.type === 'tag' && column.tagMap" :type="column.tagMap[String(row[column.prop])]?.type || 'info'">
              {{ column.tagMap[String(row[column.prop])]?.text || cellText(row, column) }}
            </el-tag>
            <span v-else>{{ cellText(row, column) }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="hasUpdate || hasRemove || $slots.actions" label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <slot name="actions" :row="row" />
            <el-button v-if="hasUpdate" link type="primary" data-test="btn-edit" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="hasRemove" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
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
        @size-change="onSearch"
      />
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId === null ? `新增${title}` : `编辑${title}`" width="640px" destroy-on-close>
      <el-form :model="form" label-width="110px">
        <el-row>
          <el-col v-for="field in formFields || []" :key="field.prop" :span="field.span || 24">
            <el-form-item :label="field.label" :required="field.required">
              <el-input
                v-if="field.type === 'input'"
                v-model="form[field.prop]"
                :placeholder="field.placeholder || `请输入${field.label}`"
                :data-test="`field-${field.prop}`"
              />
              <el-input
                v-else-if="field.type === 'textarea'"
                v-model="form[field.prop]"
                type="textarea"
                :rows="3"
                :placeholder="field.placeholder || `请输入${field.label}`"
              />
              <el-input-number
                v-else-if="field.type === 'number'"
                v-model="form[field.prop]"
                :controls="false"
                style="width: 100%"
              />
              <el-select
                v-else-if="field.type === 'select'"
                v-model="form[field.prop]"
                :placeholder="field.placeholder || `请选择${field.label}`"
                :data-test="`field-${field.prop}`"
                style="width: 100%"
              >
                <el-option v-for="opt in field.options" :key="String(opt.value)" :label="opt.label" :value="opt.value" />
              </el-select>
              <el-date-picker
                v-else-if="field.type === 'date'"
                v-model="form[field.prop]"
                type="date"
                value-format="YYYY-MM-DD"
                :placeholder="field.placeholder || `请选择${field.label}`"
                style="width: 100%"
              />
              <el-switch v-else-if="field.type === 'switch'" v-model="form[field.prop]" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" data-test="btn-save" @click="onSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.search-form {
  margin-bottom: 0;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
