import { ref, type Ref } from 'vue'

import request from '@/utils/request'
import { fetchAllOptions } from '@/utils/options'

/**
 * 统一业务对象（客户 / 商品 / 分类 / 厂家 / 供应商 / 仓库 / 员工 / 部门）的候选数据来源。
 *
 * 统一约定：
 * - 展示格式一律「编码 - 名称」；商品的编码就是 SKU，厂家没有编码则只显示名称；
 * - 数据量小的对象首屏一次性拉全量并全站缓存（整场会话只拉一次），由控件本地 `filterable`
 *   匹配（label 里带编码，所以输入编码片段或名称片段都能命中）；
 * - 数据量大的对象（客户 1650 条）走服务端 `keyword` 搜索，避免把上千条塞进下拉；
 * - 主数据变更后调用 `refreshEntityOptions()` 主动失效缓存。
 *
 * 候选数据只由 `components/EntitySelect.vue`（及各对象的薄封装）消费，页面不要再自己
 * `fetchAllOptions('/products')` 这类全量拉取。
 */
export type EntityKey =
  | 'customer'
  | 'product'
  | 'category'
  | 'manufacturer'
  | 'supplier'
  | 'warehouse'
  | 'employee'
  | 'department'

export interface CatalogOption {
  id: number
  name: string
  code?: string | null
  sku?: string | null
  [key: string]: unknown
}

export interface EntityConfig {
  key: EntityKey
  /** 中文名：占位符、form label 缺省文案用 */
  label: string
  /** 列表接口路径 */
  path: string
  /** 编码字段：商品是 SKU，厂家没有编码 */
  codeField?: string
  /** 是否走服务端关键词搜索（数据量大） */
  remote: boolean
}

export const ENTITY_CONFIGS: Record<EntityKey, EntityConfig> = {
  customer: { key: 'customer', label: '客户', path: '/customers', codeField: 'code', remote: true },
  product: { key: 'product', label: '商品', path: '/products', codeField: 'sku', remote: false },
  category: { key: 'category', label: '分类', path: '/categories', codeField: 'code', remote: false },
  manufacturer: { key: 'manufacturer', label: '厂家', path: '/manufacturers', remote: false },
  supplier: { key: 'supplier', label: '供应商', path: '/suppliers', codeField: 'code', remote: false },
  warehouse: { key: 'warehouse', label: '仓库', path: '/warehouses', codeField: 'code', remote: false },
  employee: { key: 'employee', label: '员工', path: '/employees', codeField: 'code', remote: false },
  department: { key: 'department', label: '部门', path: '/departments', codeField: 'code', remote: false },
}

export function entityConfig(entity: EntityKey): EntityConfig {
  return ENTITY_CONFIGS[entity]
}

/** 值是否是合法的业务对象键（用于动态对象字段的兜底判断）。 */
export function isEntityKey(value: unknown): value is EntityKey {
  return typeof value === 'string' && value in ENTITY_CONFIGS
}

/** 对象的编码值（商品取 SKU；厂家没有编码返回空串）。 */
export function entityCode(entity: EntityKey, row: Record<string, unknown>): string {
  const field = entityConfig(entity).codeField
  if (!field) return ''
  const value = row[field]
  return value === null || value === undefined ? '' : String(value)
}

/** 统一展示文本：`编码 - 名称`；没有编码的对象只显示名称。 */
export function entityLabel(entity: EntityKey, row: Record<string, unknown>): string {
  const name = row.name === null || row.name === undefined ? '' : String(row.name)
  const code = entityCode(entity, row)
  if (code && name) return `${code} - ${name}`
  return code || name
}

interface CacheEntry {
  options: Ref<CatalogOption[]>
  loading: Ref<boolean>
  inflight: Promise<CatalogOption[]> | null
}

const caches = new Map<EntityKey, CacheEntry>()

function cacheOf(entity: EntityKey): CacheEntry {
  let entry = caches.get(entity)
  if (!entry) {
    entry = { options: ref<CatalogOption[]>([]), loading: ref(false), inflight: null }
    caches.set(entity, entry)
  }
  return entry
}

function track(entity: EntityKey, promise: Promise<CatalogOption[]>): Promise<CatalogOption[]> {
  const entry = cacheOf(entity)
  entry.loading.value = true
  entry.inflight = promise
    .then((list) => {
      entry.options.value = list
      return list
    })
    .finally(() => {
      entry.inflight = null
      entry.loading.value = false
    })
  return entry.inflight
}

/** 取候选（已缓存则直接返回，不会重复请求）。 */
export function ensureEntityOptions(entity: EntityKey): Promise<CatalogOption[]> {
  const entry = cacheOf(entity)
  if (entry.options.value.length) return Promise.resolve(entry.options.value)
  if (entry.inflight) return entry.inflight
  return track(entity, fetchAllOptions<CatalogOption>(entityConfig(entity).path))
}

/** 使缓存失效并重新拉取（该对象新增/编辑/删除后调用）。 */
export function refreshEntityOptions(entity: EntityKey): Promise<CatalogOption[]> {
  const entry = cacheOf(entity)
  entry.options.value = []
  entry.inflight = null
  return track(entity, fetchAllOptions<CatalogOption>(entityConfig(entity).path))
}

/** 服务端关键词搜索（名称 / 编码），用于大数据量对象。 */
export async function searchEntityOptions(
  entity: EntityKey,
  keyword: string,
): Promise<CatalogOption[]> {
  const data = (await request.get(entityConfig(entity).path, {
    // 带关键词时按接口上限（1000）取，避免短前缀的候选被截断把目标挤掉：
    // 实测「北京」匹配 104 家客户，只取 50 条时排在第 98 位的客户根本搜不到。
    // 空关键词（点开下拉的初始候选）仍只取一页。
    params: { keyword: keyword || undefined, page: 1, size: keyword ? 1000 : 50 },
  })) as unknown as { items: CatalogOption[] }
  return data.items || []
}

/** 按主键取单个对象，用于编辑态回填下拉显示文本。 */
export async function getEntityOption(
  entity: EntityKey,
  id: number,
): Promise<CatalogOption | null> {
  try {
    const row = (await request.get(
      `${entityConfig(entity).path}/${id}`,
    )) as unknown as CatalogOption
    return row && row.id ? row : null
  } catch {
    return null
  }
}
