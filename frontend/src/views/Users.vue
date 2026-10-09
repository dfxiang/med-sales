<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { roleApi, userApi } from '@/api/system'
import { useUserStore } from '@/stores/user'
import request from '@/utils/request'
import { fetchAllOptions } from '@/utils/options'

interface UserRow {
  id: number
  username: string
  is_active: boolean
  created_at: string
  roles: { id: number; name: string }[]
}

const rows = ref<UserRow[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const keyword = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const form = ref({ username: '', password: '', is_active: true })
const roleOptions = ref<{ id: number; name: string }[]>([])
const bindRoleVisible = ref(false)
const bindUserId = ref<number | null>(null)
const bindRoleIds = ref<number[]>([])

const userStore = useUserStore()
const canManageUser = computed(() => userStore.hasPermission('system:user:manage'))
const canViewRoles = computed(() => userStore.hasPermission('system:role:view'))
const currentUserId = computed(() => userStore.userInfo?.id ?? null)

async function load() {
  const params: Record<string, unknown> = { page: page.value, size: size.value }
  if (keyword.value) params.keyword = keyword.value
  const data = (await userApi.list(params)) as { items: UserRow[]; total: number }
  rows.value = data.items
  total.value = data.total
}

function onSizeChange() {
  page.value = 1
  load()
}

async function loadRoles() {
  if (!canViewRoles.value) return
  roleOptions.value = await fetchAllOptions<{ id: number; name: string }>('/roles')
}

function openCreate() {
  editingId.value = null
  form.value = { username: '', password: '', is_active: true }
  dialogVisible.value = true
}

function openEdit(row: UserRow) {
  editingId.value = row.id
  form.value = { username: row.username, password: '', is_active: row.is_active }
  dialogVisible.value = true
}

async function onSubmit() {
  if (!form.value.username || (!editingId.value && !form.value.password)) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await userApi.update(editingId.value, { password: form.value.password || undefined, is_active: form.value.is_active })
      ElMessage.success('更新成功')
    } else {
      await userApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function onDelete(row: UserRow) {
  await ElMessageBox.confirm('确定删除该用户吗？', '提示', { type: 'warning' })
  await userApi.remove(row.id)
  ElMessage.success('删除成功')
  await load()
}

function openBindRoles(row: UserRow) {
  bindUserId.value = row.id
  bindRoleIds.value = row.roles.map((r) => r.id)
  bindRoleVisible.value = true
}

async function submitBindRoles() {
  if (bindUserId.value === null) return
  await userApi.bindRoles(bindUserId.value, bindRoleIds.value)
  ElMessage.success('角色分配成功')
  bindRoleVisible.value = false
  await load()
}

onMounted(() => {
  load()
  loadRoles()
})
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form inline>
        <el-form-item label="用户名">
          <el-input v-model="keyword" placeholder="请输入用户名" data-test="search-keyword" clearable style="width: 180px" @keyup.enter="page = 1; load()" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" data-test="btn-search" @click="page = 1; load()">查询</el-button>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button v-if="canManageUser" type="primary" data-test="btn-create" @click="openCreate">新增</el-button>
      </div>
    </div>
    <el-table :data="rows" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" width="160" />
      <el-table-column label="角色" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="role in row.roles" :key="role.id" class="role-tag">{{ role.name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">{{ String(row.created_at).replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
      <el-table-column label="操作" :show-overflow-tooltip="false" width="220" fixed="right">
        <template #default="{ row }">
          <template v-if="canManageUser">
            <el-button link type="primary" data-test="btn-bind-roles" @click="openBindRoles(row)">分配角色</el-button>
            <el-button link type="primary" data-test="btn-edit" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.id !== currentUserId" link type="danger" data-test="btn-delete" @click="onDelete(row)">删除</el-button>
          </template>
          <span v-if="row.id === currentUserId" class="self-tip">当前账号</span>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" v-model:page-size="size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" class="pagination" @current-change="load" @size-change="onSizeChange" />
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId === null ? '新增用户' : '编辑用户'" width="480px">
    <el-form :model="form" label-width="90px">
      <el-form-item label="用户名" required>
        <el-input v-model="form.username" :disabled="editingId !== null" data-test="field-username" />
      </el-form-item>
      <el-form-item :label="editingId === null ? '密码' : '新密码'">
        <el-input v-model="form.password" type="password" show-password data-test="field-password" />
      </el-form-item>
      <el-form-item label="启用">
        <el-switch v-model="form.is_active" :disabled="editingId !== null && editingId === currentUserId" />
        <span v-if="editingId !== null && editingId === currentUserId" class="self-tip">不能停用当前登录账号</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" data-test="btn-save" @click="onSubmit">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="bindRoleVisible" title="分配角色" width="480px">
    <el-checkbox-group v-model="bindRoleIds">
      <el-checkbox v-for="role in roleOptions" :key="role.id" :value="role.id">{{ role.name }}</el-checkbox>
    </el-checkbox-group>
    <template #footer>
      <el-button @click="bindRoleVisible = false">取消</el-button>
      <el-button type="primary" data-test="btn-save-roles" @click="submitBindRoles">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.role-tag {
  margin-right: 4px;
}
.self-tip {
  margin-left: 6px;
  color: #909399;
  font-size: 12px;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
