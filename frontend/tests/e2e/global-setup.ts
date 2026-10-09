import { request } from '@playwright/test'

/** 在每次 E2E 运行前，通过 API 预置基础主数据（数据库已在启动时重置）。 */
export default async function globalSetup() {
  const ctx = await request.newContext({ baseURL: 'http://127.0.0.1:8002' })
  // 等待 E2E 后端就绪
  let ready = false
  for (let i = 0; i < 60; i += 1) {
    try {
      const resp = await ctx.get('/')
      if (resp.ok()) {
        ready = true
        break
      }
    } catch {
      // 未就绪，继续等待
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
  if (!ready) {
    throw new Error('E2E 后端 8002 未就绪')
  }
  const login = await ctx.post('/api/auth/login', { data: { username: 'admin', password: 'admin123' } })
  if (!login.ok()) {
    throw new Error(`E2E 登录失败: ${login.status()} ${await login.text()}`)
  }
  const token = (await login.json()).access_token
  const headers = { Authorization: `Bearer ${token}` }

  async function create(path: string, data: Record<string, unknown>) {
    const resp = await ctx.post(`/api${path}`, { headers, data })
    if (!resp.ok()) {
      throw new Error(`种子数据创建失败 ${path}: ${resp.status()} ${await resp.text()}`)
    }
    return (await resp.json()).id as number
  }

  const deptId = await create('/departments', { code: 'D001', name: '销售管理部' })
  const empId = await create('/employees', {
    code: 'E0001', name: '张三', department_id: deptId, hire_date: '2026-01-01',
  })
  const whId = await create('/warehouses', { code: 'WH-001', name: '上海中心仓', has_cold_chain: true })
  const catId = await create('/categories', { code: 'CAT-DRUG', name: '化学药品' })
  const mfId = await create('/manufacturers', { name: '测试制药' })
  const supId = await create('/suppliers', { code: 'SUP001', name: '测试供应商' })
  const prodId = await create('/products', {
    sku: 'SKU-E2E-001', name: '测试药品', category_id: catId, manufacturer_id: mfId, supplier_id: supId,
    cost_price: 10, standard_price: 15, listed_date: '2026-01-01',
  })
  const custId = await create('/customers', { code: 'C00001', name: '测试医院', credit_limit: 1000000 })
  // 「管理员」角色与内置 all 权限由 E2E 后端启动脚本 create_admin.py 负责创建（含权限清单同步），
  // 这里不再重复 POST，避免每次运行都产生两条必然失败的 400 请求。
  await ctx.post('/api/inventory/open-stock', {
    headers,
    data: { warehouse_id: whId, movement_date: '2026-01-01', items: [{ product_id: prodId, quantity: 1000 }] },
  })

  process.env.E2E_SEED = JSON.stringify({ deptId, empId, whId, catId, mfId, supId, prodId, custId })
  await ctx.dispose()
}

export function seed(): Record<string, number> {
  return JSON.parse(process.env.E2E_SEED || '{}')
}
