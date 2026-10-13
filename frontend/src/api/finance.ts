import request from '@/utils/request'

export const paymentApi = {
  list: (params: Record<string, unknown>) => request.get('/payments', { params }),
  create: (data: Record<string, unknown>) => request.post('/payments', data),
  remove: (id: number) => request.delete(`/payments/${id}`),
}

export const receivableApi = {
  list: (params: Record<string, unknown>) => request.get('/receivables', { params }),
}
