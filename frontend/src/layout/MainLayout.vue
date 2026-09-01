<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const route = useRoute()
const router = useRouter()

const menuGroups = [
  {
    title: '工作台',
    items: [{ path: '/dashboard', title: '经营看板' }],
  },
  {
    title: '系统管理',
    items: [
      { path: '/system/users', title: '用户管理' },
      { path: '/system/roles', title: '角色权限' },
      { path: '/system/permissions', title: '权限管理' },
      { path: '/system/logs', title: '操作日志' },
    ],
  },
  {
    title: '组织与员工',
    items: [
      { path: '/org/departments', title: '部门管理' },
      { path: '/org/employees', title: '员工管理' },
    ],
  },
  {
    title: '主数据',
    items: [
      { path: '/customers', title: '客户管理' },
      { path: '/products', title: '商品管理' },
      { path: '/products/categories', title: '商品分类' },
      { path: '/products/manufacturers', title: '生产厂家' },
      { path: '/products/prices', title: '价格调整' },
      { path: '/suppliers', title: '供应商管理' },
      { path: '/warehouses', title: '仓库管理' },
    ],
  },
  {
    title: 'GSP 合规',
    items: [
      { path: '/gsp/certificates', title: '证照管理' },
      { path: '/gsp/batches', title: '批次管理' },
    ],
  },
]

const activeMenu = computed(() => route.path)

async function onLogout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <el-container class="main-layout">
    <el-aside width="220px" class="layout-aside">
      <div class="logo">医药销售管理系统</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="#c0c4cc"
        active-text-color="#ffffff"
        data-test="main-menu"
      >
        <template v-for="group in menuGroups" :key="group.title">
          <el-menu-item-group :title="group.title">
            <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path" data-test="menu-item">
              {{ item.title }}
            </el-menu-item>
          </el-menu-item-group>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <div class="header-title">{{ route.meta.title || '' }}</div>
        <el-dropdown>
          <span class="user-info" data-test="user-name">{{ userStore.username }}</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item data-test="logout" @click="onLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.main-layout {
  height: 100vh;
}
.layout-aside {
  background: #001529;
  overflow-y: auto;
}
.logo {
  color: #fff;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  line-height: 60px;
}
.layout-aside :deep(.el-menu) {
  border-right: none;
}
.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
}
.header-title {
  font-size: 16px;
  font-weight: 600;
}
.user-info {
  cursor: pointer;
}
</style>
