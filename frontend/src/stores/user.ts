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
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    username: localStorage.getItem('username') || '',
    userInfo: null as UserInfo | null,
  }),
  actions: {
    async login(username: string, password: string) {
      const data = (await request.post('/auth/login', { username, password })) as LoginResponse
      this.token = data.access_token
      this.username = username
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('username', username)
    },
    async fetchMe() {
      this.userInfo = (await request.get('/auth/me')) as UserInfo
      return this.userInfo
    },
    logout() {
      this.token = ''
      this.username = ''
      this.userInfo = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
    },
  },
})
