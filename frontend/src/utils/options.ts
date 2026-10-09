import request from '@/utils/request'

interface Paged<T> {
  items: T[]
  total: number
}

/**
 * 拉取列表接口的全部数据（自动翻页），用于下拉框选项。
 *
 * 背景：列表接口默认每页 20 条、上限 200 条，若直接 `list({ page: 1, size: 200 })`
 * 会导致数据量超过 200 的下拉框（如商品 365、客户 1650）缺失选项。
 */
export async function fetchAllOptions<T = Record<string, unknown>>(
  path: string,
  params: Record<string, unknown> = {},
): Promise<T[]> {
  const size = 200
  const all: T[] = []
  for (let page = 1; page <= 100; page += 1) {
    const data = (await request.get(path, {
      params: { ...params, page, size },
    })) as unknown as Paged<T>
    const items = data.items || []
    all.push(...items)
    if (items.length === 0 || all.length >= (data.total || 0)) break
  }
  return all
}
