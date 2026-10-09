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
    items: [{ path: '/dashboard', title: '经营看板', permission: 'dashboard:view' }],
  },
  {
    title: '系统管理',
    items: [
      { path: '/system/users', title: '用户管理', permission: 'system:user:view' },
      { path: '/system/roles', title: '角色权限', permission: 'system:role:view' },
      { path: '/system/permissions', title: '权限管理', permission: 'system:permission:view' },
      { path: '/system/logs', title: '操作日志', permission: 'system:log:view' },
    ],
  },
  {
    title: '组织与员工',
    items: [
      { path: '/org/departments', title: '部门管理', permission: 'org:department:view' },
      { path: '/org/employees', title: '员工管理', permission: 'org:employee:view' },
    ],
  },
  {
    title: '主数据',
    items: [
      { path: '/customers', title: '客户管理', permission: 'customer:view' },
      { path: '/products', title: '商品管理', permission: 'product:view' },
      { path: '/products/categories', title: '商品分类', permission: 'product:view' },
      { path: '/products/manufacturers', title: '生产厂家', permission: 'product:view' },
      { path: '/products/prices', title: '价格调整', permission: 'product:view' },
      { path: '/suppliers', title: '供应商管理', permission: 'supplier:view' },
      { path: '/warehouses', title: '仓库管理', permission: 'warehouse:view' },
    ],
  },
  {
    title: '进销存',
    items: [
      { path: '/purchase/orders', title: '采购订单', permission: 'purchase:view' },
      { path: '/sales/orders', title: '销售订单', permission: 'sales:view' },
      { path: '/inventory/stock', title: '库存查询', permission: 'inventory:view' },
      { path: '/inventory/movements', title: '库存流水', permission: 'inventory:view' },
      { path: '/inventory/opening', title: '期初建账', permission: 'inventory:manage' },
      { path: '/returns', title: '退货管理', permission: 'return:view' },
    ],
  },
  {
    title: '财务',
    items: [
      { path: '/finance/payments', title: '收款记录', permission: 'finance:view' },
      { path: '/finance/receivables', title: '应收账龄', permission: 'finance:view' },
    ],
  },
  {
    title: '报表分析',
    items: [
      { path: '/reports/sales', title: '销售报表', permission: 'report:view' },
      { path: '/reports/customers', title: '客户汇总', permission: 'report:view' },
      { path: '/reports/employees', title: '销售员业绩', permission: 'report:view' },
      { path: '/reports/products', title: '商品汇总', permission: 'report:view' },
      { path: '/reports/orders', title: '订单明细', permission: 'report:view' },
      { path: '/reports/inventory', title: '库存状态', permission: 'report:view' },
    ],
  },
  {
    title: 'GSP 合规',
    items: [
      { path: '/gsp/certificates', title: '证照管理', permission: 'gsp:view' },
      { path: '/gsp/qualification', title: '资质档案', permission: 'gsp:view' },
      { path: '/gsp/alerts', title: '预警中心', permission: 'gsp:view' },
      { path: '/gsp/batches', title: '批次管理', permission: 'gsp:view' },
    ],
  },
]

const activeMenu = computed(() => route.path)

/** 只展示当前账号有权限访问的菜单分组 */
const visibleGroups = computed(() =>
  menuGroups
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => userStore.hasPermission(item.permission)),
    }))
    .filter((group) => group.items.length > 0),
)

const roleNames = computed(() => (userStore.userInfo?.roles || []).map((role) => role.name).join('、'))

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
        <template v-for="group in visibleGroups" :key="group.title">
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
              <el-dropdown-item v-if="roleNames" disabled data-test="user-roles">角色：{{ roleNames }}</el-dropdown-item>
              <el-dropdown-item v-else disabled>角色：（未分配）</el-dropdown-item>
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
