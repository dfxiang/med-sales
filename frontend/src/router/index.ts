import { createRouter, createWebHistory } from 'vue-router'

import { useUserStore } from '@/stores/user'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '经营看板' } },

      // 系统管理
      { path: 'system/users', name: 'users', component: () => import('@/views/Users.vue'), meta: { title: '用户管理' } },
      { path: 'system/roles', name: 'roles', component: () => import('@/views/Roles.vue'), meta: { title: '角色权限' } },
      { path: 'system/permissions', name: 'permissions', component: () => import('@/views/Permissions.vue'), meta: { title: '权限管理' } },
      { path: 'system/logs', name: 'logs', component: () => import('@/views/AuditLogs.vue'), meta: { title: '操作日志' } },

      // 组织与员工
      { path: 'org/departments', name: 'departments', component: () => import('@/views/Departments.vue'), meta: { title: '部门管理' } },
      { path: 'org/employees', name: 'employees', component: () => import('@/views/Employees.vue'), meta: { title: '员工管理' } },

      // 主数据
      { path: 'customers', name: 'customers', component: () => import('@/views/Customers.vue'), meta: { title: '客户管理' } },
      { path: 'products', name: 'products', component: () => import('@/views/Products.vue'), meta: { title: '商品管理' } },
      { path: 'products/categories', name: 'categories', component: () => import('@/views/Categories.vue'), meta: { title: '商品分类' } },
      { path: 'products/manufacturers', name: 'manufacturers', component: () => import('@/views/Manufacturers.vue'), meta: { title: '生产厂家' } },
      { path: 'products/prices', name: 'prices', component: () => import('@/views/PriceHistory.vue'), meta: { title: '价格调整' } },
      { path: 'suppliers', name: 'suppliers', component: () => import('@/views/Suppliers.vue'), meta: { title: '供应商管理' } },
      { path: 'warehouses', name: 'warehouses', component: () => import('@/views/Warehouses.vue'), meta: { title: '仓库管理' } },

      // 进销存业务
      { path: 'purchase/orders', name: 'purchase-orders', component: () => import('@/views/PurchaseOrders.vue'), meta: { title: '采购订单' } },
      { path: 'sales/orders', name: 'sales-orders', component: () => import('@/views/SalesOrders.vue'), meta: { title: '销售订单' } },
      { path: 'inventory/stock', name: 'inventory', component: () => import('@/views/Inventory.vue'), meta: { title: '库存查询' } },
      { path: 'inventory/movements', name: 'movements', component: () => import('@/views/Movements.vue'), meta: { title: '库存流水' } },
      { path: 'inventory/opening', name: 'open-stock', component: () => import('@/views/OpenStock.vue'), meta: { title: '期初建账' } },
      { path: 'returns', name: 'returns', component: () => import('@/views/Returns.vue'), meta: { title: '退货管理' } },
      { path: 'finance/payments', name: 'payments', component: () => import('@/views/Payments.vue'), meta: { title: '收款记录' } },
      { path: 'finance/receivables', name: 'receivables', component: () => import('@/views/Receivables.vue'), meta: { title: '应收账龄' } },

      // 报表分析
      { path: 'reports/sales', name: 'reports-sales', component: () => import('@/views/SalesReports.vue'), meta: { title: '销售报表' } },
      { path: 'reports/customers', name: 'reports-customers', component: () => import('@/views/CustomerSummary.vue'), meta: { title: '客户汇总' } },
      { path: 'reports/employees', name: 'reports-employees', component: () => import('@/views/EmployeeSummary.vue'), meta: { title: '销售员业绩' } },
      { path: 'reports/products', name: 'reports-products', component: () => import('@/views/ProductSummary.vue'), meta: { title: '商品汇总' } },
      { path: 'reports/orders', name: 'reports-orders', component: () => import('@/views/OrderDetail.vue'), meta: { title: '订单明细' } },
      { path: 'reports/inventory', name: 'reports-inventory', component: () => import('@/views/InventoryStatus.vue'), meta: { title: '库存状态' } },

      // GSP 合规
      { path: 'gsp/certificates', name: 'certificates', component: () => import('@/views/Certificates.vue'), meta: { title: '证照管理' } },
      { path: 'gsp/qualification', name: 'gsp-qualification', component: () => import('@/views/Qualification.vue'), meta: { title: '资质档案' } },
      { path: 'gsp/alerts', name: 'gsp-alerts', component: () => import('@/views/GspAlerts.vue'), meta: { title: 'GSP 预警中心' } },
      { path: 'gsp/batches', name: 'batches', component: () => import('@/views/Batches.vue'), meta: { title: '批次管理' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const user = useUserStore()
  if (to.meta.public) {
    return true
  }
  if (!user.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
