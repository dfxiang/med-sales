import request from '@/utils/request'

export const customerApi = {
  list: (params: Record<string, unknown>) => request.get('/customers', { params }),
  create: (data: Record<string, unknown>) => request.post('/customers', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/customers/${id}`, data),
  remove: (id: number) => request.delete(`/customers/${id}`),
}
