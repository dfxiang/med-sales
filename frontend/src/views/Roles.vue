<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { roleApi } from '@/api/system'
import { fetchAllOptions } from '@/utils/options'

interface RoleRow {
  id: number
  name: string
  description: string | null
  permissions: { id: number; code: string; name: string }[]
}

const rows = ref<RoleRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({ name: '', description: '' })
const permissionOptions = ref<{ id: number; name: string; code: string }[]>([])
const bindVisible = ref(false)
const bindRoleId = ref<number | null>(null)
const bindPermissionIds = ref<number[]>([])

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
  permissionOptions.value = await fetchAllOptions<{ id: number; name: string; code: string }>(
    '/permissions',
  )
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
  await ElMessageBox.confirm('确定删除该角色吗？', '提示', { type: 'warning' })
  await roleApi.remove(row.id)
  ElMessage.success('删除成功')
  await load()
}

function openBind(row: RoleRow) {
  bindRoleId.value = row.id
  bindPermissionIds.value = row.permissions.map((p) => p.id)
  bindVisible.value = true
}

async function submitBind() {
  if (bindRoleId.value === null) return
  await roleApi.bindPermissions(bindRoleId.value, bindPermissionIds.value)
  ElMessage.success('权限分配成功')
  bindVisible.value = false
  await load()
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
        <el-button type="primary" data-test="btn-create" @click="openCreate">新增</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="角色名称" width="180" />
      <el-table-column prop="description" label="说明" min-width="180" />
      <el-table-column label="权限" min-width="220">
        <template #default="{ row }">
          <el-tag v-for="p in row.permissions" :key="p.id" class="perm-tag">{{ p.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" data-test="btn-bind-perms" @click="openBind(row)">分配权限</el-button>
          <el-button link type="primary" data-test="btn-edit" @click="openEdit(row)">编辑</el-button>
          <el-button link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
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

  <el-dialog v-model="bindVisible" title="分配权限" width="520px">
    <el-checkbox-group v-model="bindPermissionIds">
      <el-checkbox v-for="p in permissionOptions" :key="p.id" :value="p.id">{{ p.name }}（{{ p.code }}）</el-checkbox>
    </el-checkbox-group>
    <template #footer>
      <el-button @click="bindVisible = false">取消</el-button>
      <el-button type="primary" data-test="btn-save-perms" @click="submitBind">保存</el-button>
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
</style>
