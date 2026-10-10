import { ref, type Ref } from 'vue'

import { fetchAllOptions } from '@/utils/options'

export interface CustomerOption {
  id: number
  name: string
}

/**
 * 客户下拉候选（客户选择控件与「客户」列名称回显共用）。
 *
 * 客户有上千条，逐页拉全量并不便宜，所以整场会话只拉一次；客户数据被修改的页面
 * （客户管理）在保存成功后调用 `refreshCustomerOptions()` 主动失效。
 */
const options = ref<CustomerOption[]>([])
const loading = ref(false)
let inflight: Promise<CustomerOption[]> | null = null

function fetchOptions(): Promise<CustomerOption[]> {
  return fetchAllOptions<CustomerOption>('/customers').then((list) => {
    options.value = list
    return list
  })
}

function track(promise: Promise<CustomerOption[]>): Promise<CustomerOption[]> {
  loading.value = true
  inflight = promise.finally(() => {
    inflight = null
    loading.value = false
  })
  return inflight
}

/** 取候选（已缓存则直接返回，不会重复请求）。 */
export function ensureCustomerOptions(): Promise<CustomerOption[]> {
  if (options.value.length) return Promise.resolve(options.value)
  if (inflight) return inflight
  return track(fetchOptions())
}

/** 使缓存失效并重新拉取（客户新增/编辑/删除后调用）。 */
export function refreshCustomerOptions(): Promise<CustomerOption[]> {
  options.value = []
  inflight = null
  return track(fetchOptions())
}

export function useCustomerOptions(): {
  options: Ref<CustomerOption[]>
  loading: Ref<boolean>
  ensure: () => Promise<CustomerOption[]>
} {
  return { options, loading, ensure: ensureCustomerOptions }
}
