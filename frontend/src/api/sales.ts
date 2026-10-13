import request from '@/utils/request'

export const salesApi = {
  list: (params: Record<string, unknown>) => request.get('/sales-orders', { params }),
  get: (id: number) => request.get(`/sales-orders/${id}`),
  create: (data: Record<string, unknown>) => request.post('/sales-orders', data),
  remove: (id: number) => request.delete(`/sales-orders/${id}`),
  ship: (id: number, delivery_date: string) =>
    request.post(`/sales-orders/${id}/ship`, { delivery_date }),
  cancel: (id: number) => request.post(`/sales-orders/${id}/cancel`),
}
