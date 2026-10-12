import request from '@/utils/request'

export const userApi = {
  list: (params: Record<string, unknown>) => request.get('/users', { params }),
  create: (data: Record<string, unknown>) => request.post('/users', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/users/${id}`, data),
  remove: (id: number) => request.delete(`/users/${id}`),
  bindRoles: (id: number, role_ids: number[]) => request.post(`/users/${id}/roles`, { role_ids }),
  resetPassword: (id: number, new_password: string) =>
    request.post(`/users/${id}/reset-password`, { new_password }),
}

/** 当前登录用户的自助接口（改资料 / 改密码 / 换头像） */
export const authApi = {
  me: () => request.get('/auth/me'),
  updateProfile: (data: Record<string, unknown>) => request.put('/auth/me', data),
  changePassword: (data: Record<string, unknown>) => request.put('/auth/me/password', data),
  uploadAvatar: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    // 不手动设置 Content-Type：交给浏览器带上 multipart 边界
    return request.put('/auth/me/avatar', form)
  },
  removeAvatar: () => request.delete('/auth/me/avatar'),
}

export const roleApi = {
  list: (params: Record<string, unknown>) => request.get('/roles', { params }),
  create: (data: Record<string, unknown>) => request.post('/roles', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/roles/${id}`, data),
  remove: (id: number) => request.delete(`/roles/${id}`),
  bindPermissions: (id: number, permission_ids: number[]) =>
    request.post(`/roles/${id}/permissions`, { permission_ids }),
}

export const permissionApi = {
  list: (params: Record<string, unknown>) => request.get('/permissions', { params }),
  create: (data: Record<string, unknown>) => request.post('/permissions', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/permissions/${id}`, data),
  remove: (id: number) => request.delete(`/permissions/${id}`),
}

export const auditLogApi = {
  list: (params: Record<string, unknown>) => request.get('/audit-logs', { params }),
}
