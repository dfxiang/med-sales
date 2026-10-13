import request from '@/utils/request'

export const warehouseApi = {
  list: (params: Record<string, unknown>) => request.get('/warehouses', { params }),
  create: (data: Record<string, unknown>) => request.post('/warehouses', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/warehouses/${id}`, data),
  remove: (id: number) => request.delete(`/warehouses/${id}`),
}
