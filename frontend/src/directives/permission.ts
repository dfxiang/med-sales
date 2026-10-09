import type { Directive } from 'vue'

import { useUserStore } from '@/stores/user'

/**
 * `v-permission="'sales:manage'"` 或 `v-permission="['sales:manage', 'sales:view']"`
 *
 * 无权限时隐藏元素（用 `display:none`，不摘除节点，避免与 Vue 的 diff 冲突）。
 * 前端隐藏只做交互收敛，真正的拦截在后端 `require_permission`，两者共用同一套编码。
 */
export const permission: Directive<HTMLElement, string | string[] | undefined> = {
  mounted(el, binding) {
    apply(el, binding.value)
  },
  updated(el, binding) {
    apply(el, binding.value)
  },
}

function apply(el: HTMLElement, value: string | string[] | undefined) {
  const store = useUserStore()
  el.style.display = store.hasPermission(value) ? '' : 'none'
}

export default permission
