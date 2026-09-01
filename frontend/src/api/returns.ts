import request from '@/utils/request'

export const returnsApi = {
  list: (params: Record<string, unknown>) => request.get('/sales-returns', { params }),
  create: (data: Record<string, unknown>) => request.post('/sales-returns', data),
  remove: (id: number) => request.delete(`/sales-returns/${id}`),
  process: (id: number) => request.post(`/sales-returns/${id}/process`),
}
