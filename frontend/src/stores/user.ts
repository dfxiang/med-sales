import { defineStore } from 'pinia'

import request from '@/utils/request'

interface LoginResponse {
  access_token: string
  token_type: string
}

interface UserInfo {
  id: number
  username: string
  display_name: string | null
  phone: string | null
  email: string | null
  avatar_url: string
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
    /** 顶栏展示名：显示名称为空时回退用户名（老数据兜底） */
    displayName: (state) => state.userInfo?.display_name || state.userInfo?.username || state.username,
    /** 头像相对地址（未设置头像时后端已回落默认头像） */
    avatarUrl: (state) => state.userInfo?.avatar_url || '/api/avatars/default.png',
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
      this.applyMe(me)
      return me
    },
    /** 把 /auth/me 的响应写入本地状态（个人资料、头像相关的自助接口复用同一逻辑） */
    applyMe(me: MeResponse) {
      this.userInfo = {
        id: me.id,
        username: me.username,
        display_name: me.display_name ?? null,
        phone: me.phone ?? null,
        email: me.email ?? null,
        avatar_url: me.avatar_url ?? '/api/avatars/default.png',
        is_active: me.is_active,
        roles: (me.roles ?? []).map((role) => ({ id: role.id, name: role.name })),
      }
      this.username = me.username
      this.permissions = me.permissions ?? []
      this.isSuperuser = Boolean(me.is_superuser)
      this.loaded = true
      localStorage.setItem('username', me.username)
    },
    /** 自助更新个人资料（显示名称 / 电话 / 邮箱） */
    async updateProfile(payload: {
      display_name?: string
      phone?: string | null
      email?: string | null
    }) {
      const me = (await request.put('/auth/me', payload)) as MeResponse
      this.applyMe(me)
      return me
    },
    /** 自助改密：需要原密码 + 两次一致的新密码（服务端会复核） */
    async changePassword(payload: {
      old_password: string
      new_password: string
      confirm_password: string
    }) {
      return request.put('/auth/me/password', payload)
    },
    /** 上传 / 更换头像（服务端统一规范化为 256×256 PNG） */
    async uploadAvatar(file: File) {
      const form = new FormData()
      form.append('file', file)
      const me = (await request.put('/auth/me/avatar', form)) as MeResponse
      this.applyMe(me)
      return me
    },
    /** 恢复默认头像 */
    async removeAvatar() {
      const me = (await request.delete('/auth/me/avatar')) as MeResponse
      this.applyMe(me)
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
