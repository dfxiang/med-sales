<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import EntitySelect from '@/components/EntitySelect.vue'
import { useUserStore } from '@/stores/user'
import { isEntityKey, type EntityKey } from '@/utils/catalogOptions'

export interface Column {
  prop: string
  label: string
  width?: number | string
  type?: 'text' | 'money' | 'date' | 'datetime' | 'tag'
  tagMap?: Record<string, { text?: string; type?: 'success' | 'warning' | 'danger' | 'info' | 'primary' }>
  /** 自定义单元格文本（优先级高于 type 派生格式） */
  formatter?: (row: Record<string, unknown>) => string
}

export interface SearchField {
  prop: string
  label: string
  type?: 'input' | 'select' | 'entity'
  /** entity 专用：统一业务对象控件（显示编码+名称，可按编码或名称搜索） */
  entity?: EntityKey
  options?: { label: string; value: string | number }[]
  /** select 专用：异步拉取候选项（如分类、供应商） */
  optionsApi?: () => Promise<Record<string, unknown>[]>
  optionLabel?: string
  optionValue?: string
  placeholder?: string
}

export interface FormField {
  prop: string
  label: string
  type: 'input' | 'number' | 'textarea' | 'select' | 'date' | 'switch' | 'remote-select' | 'entity'
  /** entity 专用：统一业务对象控件（显示编码+名称，可按编码或名称搜索） */
  entity?: EntityKey
  /** entity 专用：对象随表单其它字段联动（如证照的「对象类型」）；返回空串表示尚未选定 */
  entityOf?: (form: Record<string, unknown>) => EntityKey | ''
  /** entity 专用：依赖的表单字段，变化时清空已选值 */
  entityDepends?: string[]
  required?: boolean
  options?: { label: string; value: string | number | boolean }[]
  optionsApi?: () => Promise<Record<string, unknown>[]>
  /** select 专用：允许输入候选项之外的值（如证照类型） */
  allowCreate?: boolean
  /** remote-select 专用：按关键词搜索候选项（可读取表单里的联动字段） */
  remoteApi?: (keyword: string, form: Record<string, unknown>) => Promise<SelectOption[]>
  /** remote-select 专用：编辑时按主键回填候选项（避免首屏列表里没有该记录） */
  remoteById?: (
    value: string | number,
    form: Record<string, unknown>,
  ) => Promise<SelectOption | null>
  /** remote-select 专用：依赖的表单字段，变化时清空并重新拉取候选 */
  remoteDepends?: string[]
  optionLabel?: string
  optionValue?: string
  placeholder?: string
  default?: unknown
  span?: number
  nullable?: boolean
  /** 字段值变化后的回调（可用于联动清空、重置等） */
  onChange?: (value: unknown, form: Record<string, unknown>) => void
}

export interface SelectOption {
  label: string
  value: string | number
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
  /** 「操作」列宽度（px），默认 200；操作按钮较多时可放宽以免换行 */
  actionColumnWidth?: number
  /** 维护类接口所需的权限编码（新增/编辑/删除）；不传则不做前端隐藏 */
  managePermission?: string
}>()

/** 新增/编辑/删除成功后触发，供父页面刷新依赖该数据的共享缓存 */
const emit = defineEmits<{ (e: 'saved'): void }>()

const userStore = useUserStore()
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
const remoteOptions = reactive<Record<string, SelectOption[]>>({})
const remoteLoading = reactive<Record<string, boolean>>({})
const searchOptions = reactive<Record<string, SelectOption[]>>({})

const hasCreate = computed(() => !!props.api.create)
const hasUpdate = computed(() => !!props.api.update)
const hasRemove = computed(() => !!props.api.remove)
/** 无维护权限时隐藏增删改按钮（后端仍会 403 兜底） */
const canManage = computed(() => userStore.hasPermission(props.managePermission))

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
  hydrateRemoteFields()
  dialogVisible.value = true
}

function openEdit(row: Record<string, unknown>) {
  editingId.value = (row as Record<string, unknown>)[props.rowKey || 'id'] as number | string
  for (const key of Object.keys(form)) delete form[key]
  for (const field of props.formFields || []) {
    form[field.prop] = row[field.prop] ?? field.default ?? ''
  }
  loadFieldOptions()
  hydrateRemoteFields()
  dialogVisible.value = true
}

async function searchRemote(field: FormField, keyword: string) {
  if (!field.remoteApi) return
  remoteLoading[field.prop] = true
  try {
    remoteOptions[field.prop] = await field.remoteApi(keyword, form)
  } catch {
    remoteOptions[field.prop] = []
  } finally {
    remoteLoading[field.prop] = false
  }
}

/** 打开弹窗时预取候选；编辑态下若当前值不在候选里，再按主键补一条。 */
async function hydrateRemoteFields() {
  for (const field of props.formFields || []) {
    if (field.type !== 'remote-select') continue
    const ready = (field.remoteDepends || []).every(
      (dep) => form[dep] !== '' && form[dep] !== undefined && form[dep] !== null,
    )
    if (!ready) {
      remoteOptions[field.prop] = []
      continue
    }
    await searchRemote(field, '')
    const value = form[field.prop]
    if (value === '' || value === undefined || value === null) continue
    const exists = (remoteOptions[field.prop] || []).some((opt) => opt.value === value)
    if (!exists && field.remoteById) {
      const option = await field.remoteById(value as string | number, form)
      if (option) {
        remoteOptions[field.prop] = [option, ...(remoteOptions[field.prop] || [])]
      }
    }
  }
}

/** 字段值变化：执行自定义回调，并让依赖它的 remote-select 重新拉取候选。 */
function onFieldChange(field: FormField, value: unknown) {
  field.onChange?.(value, form)
  for (const target of props.formFields || []) {
    if (target.type === 'entity' && target.entityDepends?.includes(field.prop)) {
      // 对象类型变了（如证照的「对象类型」）：清掉已选主体，避免提交错对象的主键
      form[target.prop] = ''
      continue
    }
    if (target.type !== 'remote-select') continue
    if (!target.remoteDepends?.includes(field.prop)) continue
    form[target.prop] = ''
    remoteOptions[target.prop] = []
    const ready = (target.remoteDepends || []).every(
      (dep) => form[dep] !== '' && form[dep] !== undefined && form[dep] !== null,
    )
    if (ready) searchRemote(target, '')
  }
}

/** entity 字段绑定的业务对象；动态对象（entityOf）读当前表单值。 */
function resolveEntity(field: FormField): EntityKey | undefined {
  const key = field.entityOf ? field.entityOf(form) : field.entity
  return isEntityKey(key) ? key : undefined
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

/** 筛选栏里的 select 候选项（静态 options 或 optionsApi 拉取）。 */
async function loadSearchOptions() {
  for (const field of props.searchFields || []) {
    if (!field.optionsApi) continue
    try {
      const data = await field.optionsApi()
      searchOptions[field.prop] = data.map((item) => ({
        label: String(item[field.optionLabel || 'name']),
        value: item[field.optionValue || 'id'] as string | number,
      }))
    } catch {
      searchOptions[field.prop] = []
    }
  }
}

function searchFieldOptions(field: SearchField): SelectOption[] {
  return searchOptions[field.prop] ?? field.options ?? []
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
    emit('saved')
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
  emit('saved')
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
  if (column.formatter) return column.formatter(row)
  const value = row[column.prop]
  if (value === null || value === undefined) return ''
  if (column.type === 'money') return Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2 })
  if (column.type === 'date') return String(value).slice(0, 10)
  if (column.type === 'datetime') return String(value).replace('T', ' ').slice(0, 19)
  return String(value)
}

onMounted(() => {
  loadSearchOptions()
  load()
})

// 供父页面在完成外部操作（如审核）后刷新列表
defineExpose({ reload: load })
</script>

<template>
  <div data-test="crud-page">
    <el-card>
      <div class="page-toolbar">
        <el-form v-if="searchFields?.length" :inline="true" class="search-form">
          <el-form-item v-for="field in searchFields" :key="field.prop" :label="field.label">
            <EntitySelect
              v-if="field.type === 'entity' && field.entity"
              v-model="searchForm[field.prop]"
              :entity="field.entity"
              width="200px"
              :data-test="`search-${field.prop}`"
            />
            <el-select
              v-else-if="field.type === 'select'"
              v-model="searchForm[field.prop]"
              clearable
              :placeholder="field.placeholder || `请选择${field.label}`"
              :data-test="`search-${field.prop}`"
              style="width: 180px"
            >
              <el-option
                v-for="opt in searchFieldOptions(field)"
                :key="String(opt.value)"
                :label="opt.label"
                :value="opt.value"
              />
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
          <el-button v-if="hasCreate && canManage" type="primary" data-test="btn-create" @click="openCreate">
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
        <el-table-column
          v-if="hasUpdate || hasRemove || $slots.actions"
          label="操作"
          :show-overflow-tooltip="false"
          :width="actionColumnWidth ?? 200"
          fixed="right"
        >
          <template #default="{ row }">
            <slot name="actions" :row="row" />
            <el-button v-if="hasUpdate && canManage" link type="primary" data-test="btn-edit" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="hasRemove && canManage" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
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
              <EntitySelect
                v-if="field.type === 'entity' && resolveEntity(field)"
                v-model="form[field.prop]"
                :entity="resolveEntity(field) as EntityKey"
                width="100%"
                :data-test="`field-${field.prop}`"
              />
              <el-select
                v-else-if="field.type === 'entity'"
                disabled
                placeholder="请先选择对象类型"
                :data-test="`field-${field.prop}`"
                style="width: 100%"
              />
              <el-select
                v-else-if="field.type === 'select'"
                v-model="form[field.prop]"
                :filterable="field.allowCreate"
                :allow-create="field.allowCreate"
                :default-first-option="field.allowCreate"
                :placeholder="field.placeholder || `请选择${field.label}`"
                :data-test="`field-${field.prop}`"
                style="width: 100%"
                @change="(value: unknown) => onFieldChange(field, value)"
              >
                <el-option v-for="opt in field.options" :key="String(opt.value)" :label="opt.label" :value="opt.value" />
              </el-select>
              <el-select
                v-else-if="field.type === 'remote-select'"
                v-model="form[field.prop]"
                filterable
                remote
                reserve-keyword
                :remote-method="(keyword: string) => searchRemote(field, keyword)"
                :loading="remoteLoading[field.prop]"
                :disabled="(field.remoteDepends || []).some((dep) => !form[dep])"
                :placeholder="field.placeholder || `请输入关键词搜索${field.label}`"
                :data-test="`field-${field.prop}`"
                style="width: 100%"
                @change="(value: unknown) => onFieldChange(field, value)"
              >
                <el-option
                  v-for="opt in remoteOptions[field.prop] || []"
                  :key="String(opt.value)"
                  :label="opt.label"
                  :value="opt.value"
                />
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
