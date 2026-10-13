import request from '@/utils/request'

export const categoryApi = {
  list: (params: Record<string, unknown>) => request.get('/categories', { params }),
  create: (data: Record<string, unknown>) => request.post('/categories', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/categories/${id}`, data),
  remove: (id: number) => request.delete(`/categories/${id}`),
}

export const manufacturerApi = {
  list: (params: Record<string, unknown>) => request.get('/manufacturers', { params }),
  create: (data: Record<string, unknown>) => request.post('/manufacturers', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/manufacturers/${id}`, data),
  remove: (id: number) => request.delete(`/manufacturers/${id}`),
}

export const productApi = {
  list: (params: Record<string, unknown>) => request.get('/products', { params }),
  create: (data: Record<string, unknown>) => request.post('/products', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/products/${id}`, data),
  remove: (id: number) => request.delete(`/products/${id}`),
  prices: (id: number, params: Record<string, unknown>) =>
    request.get(`/products/${id}/prices`, { params }),
  adjustPrice: (id: number, data: Record<string, unknown>) =>
    request.post(`/products/${id}/prices`, data),
}
