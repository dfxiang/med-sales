import request from '@/utils/request'

export const purchaseApi = {
  list: (params: Record<string, unknown>) => request.get('/purchase-orders', { params }),
  get: (id: number) => request.get(`/purchase-orders/${id}`),
  create: (data: Record<string, unknown>) => request.post('/purchase-orders', data),
  remove: (id: number) => request.delete(`/purchase-orders/${id}`),
  receive: (id: number, data: Record<string, unknown>) =>
    request.post(`/purchase-orders/${id}/receive`, data),
}
