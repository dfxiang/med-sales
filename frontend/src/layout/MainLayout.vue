<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

import ChangePasswordDialog from '@/components/ChangePasswordDialog.vue'
import PreferenceControls from '@/components/PreferenceControls.vue'
import ProfileDialog from '@/components/ProfileDialog.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import { useUserStore } from '@/stores/user'
import { avatarSrc } from '@/utils/avatar'

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
const profileVisible = ref(false)
const passwordVisible = ref(false)

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
        <div class="header-actions">
          <PreferenceControls />
          <el-dropdown>
            <span class="user-info">
              <UserAvatar
                class="header-avatar"
                :src="avatarSrc(userStore.avatarUrl)"
                :size="32"
                :name="userStore.displayName"
                data-test="header-avatar"
              />
              <span class="user-name" data-test="user-name">{{ userStore.displayName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="roleNames" disabled data-test="user-roles">角色：{{ roleNames }}</el-dropdown-item>
                <el-dropdown-item v-else disabled>角色：（未分配）</el-dropdown-item>
                <el-dropdown-item disabled data-test="user-email">
                  邮箱：{{ userStore.userInfo?.email || '未填写' }}
                </el-dropdown-item>
                <el-dropdown-item disabled data-test="user-phone">
                  电话：{{ userStore.userInfo?.phone || '未填写' }}
                </el-dropdown-item>
                <el-dropdown-item divided data-test="profile-entry" @click="profileVisible = true">个人资料</el-dropdown-item>
                <el-dropdown-item data-test="password-entry" @click="passwordVisible = true">修改密码</el-dropdown-item>
                <el-dropdown-item data-test="logout" @click="onLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
      <el-footer class="layout-footer" height="52px" data-test="layout-footer">
        <span class="footer-project">医药销售管理系统</span>
        <span class="footer-separator" aria-hidden="true"></span>
        <a
          class="footer-link"
          href="https://github.com/dfxiang/med-sales"
          target="_blank"
          rel="noopener noreferrer"
          data-test="footer-github"
        >
          <span class="footer-link-label">GitHub 开源地址</span>
        </a>
        <span class="footer-separator" aria-hidden="true"></span>
        <span class="footer-author" data-test="footer-author">
          <span>作者：</span><span>Danny Xiang, Wuhan, China</span>
        </span>
        <span class="footer-separator" aria-hidden="true"></span>
        <span class="footer-wechat" data-test="footer-wechat">
          <span>微信：</span><span>4198166</span>
        </span>
      </el-footer>
    </el-container>
  </el-container>

  <ProfileDialog v-model="profileVisible" />
  <ChangePasswordDialog v-model="passwordVisible" />
</template>

<style scoped>
.main-layout {
  height: 100vh;
}
.layout-aside {
  background: var(--layout-aside-bg);
  border-right: 1px solid var(--layout-aside-border);
  overflow-y: auto;
}
.logo {
  border-bottom: 1px solid var(--layout-aside-border);
  color: var(--layout-aside-text);
  padding: 0 16px;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  line-height: 60px;
}
.layout-aside :deep(.el-menu) {
  border-right: none;
  --el-menu-bg-color: var(--layout-aside-bg);
  --el-menu-text-color: var(--layout-aside-muted);
  --el-menu-active-color: var(--layout-aside-active-text);
  --el-menu-hover-bg-color: var(--layout-aside-hover);
  --el-menu-hover-text-color: var(--layout-aside-text);
  --el-menu-item-height: 44px;
}
.layout-aside :deep(.el-menu-item-group__title) {
  color: var(--layout-aside-muted);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.02em;
}
.layout-aside :deep(.el-menu-item) {
  margin: 2px 8px;
  border-radius: 8px;
  line-height: 44px;
}
.layout-aside :deep(.el-menu-item.is-active) {
  background: var(--layout-aside-active-bg);
  font-weight: 650;
}
.layout-header {
  display: flex;
  height: 60px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
}
.layout-footer {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 14px;
  overflow: hidden;
  padding: 0 20px;
  border-top: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1;
}
.footer-project {
  min-width: 0;
  overflow: hidden;
  flex: 1 1 auto;
  color: var(--el-text-color-regular);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.footer-separator {
  width: 1px;
  height: 14px;
  flex: none;
  background: var(--el-border-color);
}
.footer-link {
  display: inline-flex;
  min-height: 32px;
  flex: none;
  align-items: center;
  gap: 6px;
  border-radius: 4px;
  color: var(--el-color-primary);
  text-decoration: none;
}
.footer-link:hover .footer-link-label {
  text-decoration: underline;
  text-underline-offset: 2px;
}
.footer-link:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}
.footer-link-label {
  font-weight: 600;
}
.footer-author,
.footer-wechat {
  flex: none;
  white-space: nowrap;
}
.header-title {
  min-width: 0;
  overflow: hidden;
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: 12px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
/* 头像不参与压缩：显示名称很长或窗口很窄时，也要保持正圆（否则会被挤成椭圆甚至挤没） */
.header-avatar {
  flex: none;
}
.user-name {
  font-size: 14px;
}
@media (max-width: 1100px) {
  .layout-footer {
    gap: 10px;
    padding-inline: 14px;
  }
}
@media (max-width: 820px) {
  .layout-footer {
    gap: 8px;
  }
  .footer-separator {
    display: none;
  }
  .footer-link {
    gap: 4px;
  }
}
</style>
