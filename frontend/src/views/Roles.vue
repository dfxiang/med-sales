<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { roleApi } from '@/api/system'
import { useUserStore } from '@/stores/user'
import { fetchAllOptions } from '@/utils/options'
import { moduleSortIndex, permissionModuleLabel } from '@/utils/permission'

interface RoleRow {
  id: number
  name: string
  description: string | null
  permissions: { id: number; code: string; name: string }[]
}

interface PermissionOption {
  id: number
  name: string
  code: string
}

interface PermissionGroup {
  key: string
  label: string
  items: PermissionOption[]
}

const userStore = useUserStore()
const rows = ref<RoleRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({ name: '', description: '' })
const permissionOptions = ref<PermissionOption[]>([])
const bindVisible = ref(false)
const bindRoleId = ref<number | null>(null)
const bindRoleName = ref('')
const bindPermissionIds = ref<number[]>([])
const permKeyword = ref('')
const bindSaving = ref(false)

const canManageRole = computed(() => userStore.hasPermission('system:role:manage'))
/** 分配权限的弹窗需要读取权限清单，单独判断，避免无权限时白跑一次 403 请求 */
const canViewPermissions = computed(() => userStore.hasPermission('system:permission:view'))

const matchedPermissions = computed(() => {
  const query = permKeyword.value.trim().toLowerCase()
  if (!query) return permissionOptions.value
  return permissionOptions.value.filter(
    (p) => p.name.toLowerCase().includes(query) || p.code.toLowerCase().includes(query),
  )
})

/** 按模块（编码第一段）分组，便于成片勾选 */
const permissionGroups = computed<PermissionGroup[]>(() => {
  const buckets = new Map<string, PermissionOption[]>()
  for (const item of matchedPermissions.value) {
    const key = item.code.split(':')[0] || 'other'
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key)!.push(item)
  }
  return [...buckets.entries()]
    .map(([key, items]) => ({
      key,
      label: permissionModuleLabel(items[0]?.code ?? key),
      items: [...items].sort(
        (a, b) => moduleSortIndex(a.code) - moduleSortIndex(b.code) || a.id - b.id,
      ),
    }))
    .sort((a, b) => moduleSortIndex(a.items[0]?.code ?? '') - moduleSortIndex(b.items[0]?.code ?? ''))
})

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (keyword.value) params.keyword = keyword.value
  const data = (await roleApi.list(params)) as { items: RoleRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSizeChange() {
  page.value = 1
  load()
}

async function loadPermissions() {
  if (!canViewPermissions.value) return
  permissionOptions.value = await fetchAllOptions<PermissionOption>('/permissions')
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', description: '' }
  dialogVisible.value = true
}

function openEdit(row: RoleRow) {
  editingId.value = row.id
  form.value = { name: row.name, description: row.description || '' }
  dialogVisible.value = true
}

async function onSubmit() {
  if (!form.value.name) {
    ElMessage.warning('请填写角色名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await roleApi.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await roleApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: RoleRow) {
  await ElMessageBox.confirm(
    `确定删除角色「${row.name}」吗？仍被账号使用的角色需要先解除关联。`,
    '提示',
    { type: 'warning' },
  )
  await roleApi.remove(row.id)
  ElMessage.success('删除成功')
  await load()
}

function openBind(row: RoleRow) {
  bindRoleId.value = row.id
  bindRoleName.value = row.name
  bindPermissionIds.value = row.permissions.map((p) => p.id)
  permKeyword.value = ''
  bindVisible.value = true
}

function groupCheckedItems(group: PermissionGroup): number[] {
  return group.items.filter((p) => bindPermissionIds.value.includes(p.id)).map((p) => p.id)
}

function isGroupAllChecked(group: PermissionGroup): boolean {
  return group.items.length > 0 && groupCheckedItems(group).length === group.items.length
}

function isGroupIndeterminate(group: PermissionGroup): boolean {
  const checked = groupCheckedItems(group).length
  return checked > 0 && checked < group.items.length
}

function toggleGroup(group: PermissionGroup, checked: boolean | string | number) {
  const ids = group.items.map((p) => p.id)
  const current = new Set(bindPermissionIds.value)
  if (checked) {
    ids.forEach((id) => current.add(id))
  } else {
    ids.forEach((id) => current.delete(id))
  }
  bindPermissionIds.value = [...current]
}

function selectAllMatched() {
  const current = new Set(bindPermissionIds.value)
  matchedPermissions.value.forEach((p) => current.add(p.id))
  bindPermissionIds.value = [...current]
}

function clearAll() {
  bindPermissionIds.value = []
}

async function submitBind() {
  if (bindRoleId.value === null) return
  bindSaving.value = true
  try {
    await roleApi.bindPermissions(bindRoleId.value, bindPermissionIds.value)
    ElMessage.success('权限分配成功')
    bindVisible.value = false
    await load()
  } finally {
    bindSaving.value = false
  }
}

onMounted(() => {
  load()
  loadPermissions()
})
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
        <el-form-item label="角色名称">
          <el-input v-model="keyword" placeholder="请输入角色名称" data-test="search-keyword" clearable style="width: 180px" @keyup.enter="page = 1; load()" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="page = 1; load()">查询</el-button>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button v-if="canManageRole" type="primary" data-test="btn-create" @click="openCreate">新增</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="角色名称" width="160" />
      <el-table-column prop="description" label="说明" width="220" />
      <el-table-column label="权限" min-width="260">
        <template #default="{ row }">
          <template v-if="row.permissions.length">
            <el-tag
              v-for="p in row.permissions"
              :key="p.id"
              class="perm-tag"
              :type="p.code === 'all' ? 'danger' : 'primary'"
            >
              {{ p.name }}
            </el-tag>
          </template>
          <el-tag v-else type="info">未分配</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" :show-overflow-tooltip="false" width="220" fixed="right">
        <template #default="{ row }">
          <el-button v-if="canManageRole" link type="primary" data-test="btn-bind-perms" @click="openBind(row)">分配权限</el-button>
          <el-button v-if="canManageRole" link type="primary" data-test="btn-edit" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="canManageRole" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSizeChange" />
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId === null ? '新增角色' : '编辑角色'" width="480px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="角色名称" required>
        <el-input v-model="form.name" data-test="field-name" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="form.description" type="textarea" data-test="field-description" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" data-test="btn-save" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="bindVisible" :title="`分配权限 - ${bindRoleName}`" width="680px">
    <div class="perm-toolbar">
      <el-input v-model="permKeyword" placeholder="搜索权限名称 / 编码" clearable data-test="perm-search" style="width: 240px" />
      <el-button link type="primary" data-test="perm-select-all" @click="selectAllMatched">全选当前结果</el-button>
      <el-button link data-test="perm-clear" @click="clearAll">清空</el-button>
      <span class="perm-count">已选 {{ bindPermissionIds.length }} / {{ permissionOptions.length }}</span>
    </div>
    <el-scrollbar max-height="420px">
      <div v-for="group in permissionGroups" :key="group.key" class="perm-group" :data-test="`perm-group-${group.key}`">
        <div class="perm-group-title">
          <el-checkbox
            :model-value="isGroupAllChecked(group)"
            :indeterminate="isGroupIndeterminate(group)"
            @change="(checked: boolean | string | number) => toggleGroup(group, checked)"
          >
            {{ group.label }}
          </el-checkbox>
          <span class="perm-group-count">{{ groupCheckedItems(group).length }}/{{ group.items.length }}</span>
        </div>
        <el-checkbox-group v-model="bindPermissionIds" class="perm-items">
          <el-checkbox
            v-for="p in group.items"
            :key="p.id"
            :value="p.id"
            :data-test="`perm-${p.code}`"
          >
            {{ p.name }}（{{ p.code }}）
          </el-checkbox>
        </el-checkbox-group>
      </div>
      <el-empty v-if="!permissionGroups.length" description="没有匹配的权限" />
    </el-scrollbar>
    <template #footer>
      <el-button @click="bindVisible = false">取消</el-button>
      <el-button type="primary" :loading="bindSaving" data-test="btn-save-perms" @click="submitBind">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.perm-tag {
  margin-right: 4px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
.perm-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.perm-count {
  margin-left: auto;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.perm-group {
  border-top: 1px solid var(--el-border-color-lighter);
  padding: 8px 0 4px;
}
.perm-group:first-child {
  border-top: none;
}
.perm-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.perm-group-count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 400;
}
.perm-items {
  display: flex;
  flex-wrap: wrap;
  padding-left: 24px;
}
.perm-items :deep(.el-checkbox) {
  width: 100%;
  margin-right: 0;
}
</style>
