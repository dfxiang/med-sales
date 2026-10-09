import { defineStore } from 'pinia'

import request from '@/utils/request'

interface LoginResponse {
  access_token: string
  token_type: string
}

interface UserInfo {
  id: number
  username: string
  is_active: boolean
  roles: { id: number; name: string }[]
}

export interface MeResponse extends UserInfo {
  employee_id: number | null
  roles: { id: number; name: string }[]
  /** 经角色继承到的权限编码；`all` 为通配权限 */
  permissions: string[]
  is_superuser: boolean
}

/** 通配权限：拥有它即视为拥有全部权限（与后端 core/permissions.py 保持一致） */
const ALL_PERMISSION = 'all'

/** 同一时刻只允许一个 /auth/me 请求，避免路由切换时重复拉取 */
let inflight: Promise<MeResponse> | null = null

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    username: localStorage.getItem('username') || '',
    userInfo: null as UserInfo | null,
    permissions: [] as string[],
    isSuperuser: false,
    /** 是否已成功拉取过 /auth/me（用于路由守卫判断是否需要先取权限） */
    loaded: false,
  }),
  getters: {
    /** 是否具备权限；不传编码视为通过；支持数组时「任一命中」即可。 */
    hasPermission: (state) => (code?: string | string[]) => {
      if (!code || (Array.isArray(code) && code.length === 0)) return true
      if (state.isSuperuser || state.permissions.includes(ALL_PERMISSION)) return true
      const codes = Array.isArray(code) ? code : [code]
      return codes.some((item) => state.permissions.includes(item))
    },
  },
  actions: {
    async login(username: string, password: string) {
      const data = (await request.post('/auth/login', { username, password })) as LoginResponse
      this.token = data.access_token
      this.username = username
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('username', username)
      await this.fetchMe()
    },
    async fetchMe() {
      if (!inflight) {
        inflight = (request.get('/auth/me') as Promise<MeResponse>).finally(() => {
          inflight = null
        })
      }
      const me = await inflight
      this.userInfo = {
        id: me.id,
        username: me.username,
        is_active: me.is_active,
        roles: (me.roles ?? []).map((role) => ({ id: role.id, name: role.name })),
      }
      this.username = me.username
      this.permissions = me.permissions ?? []
      this.isSuperuser = Boolean(me.is_superuser)
      this.loaded = true
      localStorage.setItem('username', me.username)
      return me
    },
    /** 权限被后台调整后强制刷新 */
    async reloadPermissions() {
      this.loaded = false
      return this.fetchMe()
    },
    logout() {
      this.token = ''
      this.username = ''
      this.userInfo = null
      this.permissions = []
      this.isSuperuser = false
      this.loaded = false
      inflight = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
    },
  },
})
