import request from '@/utils/request'

export interface EntityOption {
  label: string
  value: number
}

/** 证照主体类型 -> 列表接口路径 */
export const ENTITY_PATHS: Record<string, string> = {
  customer: '/customers',
  supplier: '/suppliers',
  product: '/products',
  manufacturer: '/manufacturers',
}

export const ENTITY_LABELS: Record<string, string> = {
  customer: '客户',
  supplier: '供应商',
  product: '商品',
  manufacturer: '生产厂家',
}

export function entityLabel(entityType: string, row: Record<string, unknown>): string {
  const name = String(row.name ?? '')
  if (entityType === 'product') return `${row.sku ?? ''} ${name}`.trim()
  const code = row.code ? `${row.code} ` : ''
  return `${code}${name}`.trim()
}

/** 远程搜索主体候选项（用于证照表单的「关联对象」选择器）。 */
export async function searchEntityOptions(
  entityType: string,
  keyword: string,
): Promise<EntityOption[]> {
  const path = ENTITY_PATHS[entityType]
  if (!path) return []
  const data = (await request.get(path, {
    params: { keyword, page: 1, size: 50 },
  })) as unknown as { items: Record<string, unknown>[] }
  return (data.items || []).map((row) => ({
    label: entityLabel(entityType, row),
    value: Number(row.id),
  }))
}

/** 按主键取单个主体，用于编辑态回填下拉显示名。 */
export async function getEntityOption(
  entityType: string,
  id: number,
): Promise<EntityOption | null> {
  const path = ENTITY_PATHS[entityType]
  if (!path) return null
  try {
    const row = (await request.get(`${path}/${id}`)) as unknown as Record<string, unknown>
    return { label: entityLabel(entityType, row), value: Number(row.id) }
  } catch {
    return null
  }
}

export function humanSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}
