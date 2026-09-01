import request from '@/utils/request'

export const supplierApi = {
  list: (params: Record<string, unknown>) => request.get('/suppliers', { params }),
  create: (data: Record<string, unknown>) => request.post('/suppliers', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/suppliers/${id}`, data),
  remove: (id: number) => request.delete(`/suppliers/${id}`),
}
