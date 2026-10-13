/**
 * 权限编码相关的展示辅助。
 *
 * 编码约定（与后端 `api/app/core/permissions.py` 一致）：`模块:动作` 或
 * `模块:对象:动作`，第一段即模块名。
 */

/** 模块编码 → 中文名 */
export const PERMISSION_MODULES: Record<string, string> = {
  all: '内置',
  dashboard: '工作台',
  system: '系统管理',
  org: '组织与员工',
  customer: '客户管理',
  product: '商品管理',
  supplier: '供应商管理',
  warehouse: '仓库管理',
  purchase: '采购管理',
  sales: '销售管理',
  inventory: '库存管理',
  return: '退货管理',
  finance: '财务',
  report: '报表分析',
  gsp: 'GSP 合规',
}

/** 模块顺序（权限分配弹窗按此顺序分组展示） */
export const PERMISSION_MODULE_ORDER = Object.keys(PERMISSION_MODULES)

export function permissionModuleKey(code: string): string {
  return (code || '').split(':')[0] || 'other'
}

export function permissionModuleLabel(code: string): string {
  const key = permissionModuleKey(code)
  return PERMISSION_MODULES[key] || key || '未分类'
}

export function moduleSortIndex(code: string): number {
  const index = PERMISSION_MODULE_ORDER.indexOf(permissionModuleKey(code))
  return index === -1 ? PERMISSION_MODULE_ORDER.length : index
}
