import request from '@/utils/request'

export const certificateApi = {
  list: (params: Record<string, unknown>) => request.get('/gsp/certificates', { params }),
  create: (data: Record<string, unknown>) => request.post('/gsp/certificates', data),
  update: (id: number, data: Record<string, unknown>) =>
    request.put(`/gsp/certificates/${id}`, data),
  remove: (id: number) => request.delete(`/gsp/certificates/${id}`),
  expiring: (days = 90) => request.get('/gsp/certificates/expiring', { params: { days } }),
}

export const batchApi = {
  list: (params: Record<string, unknown>) => request.get('/gsp/batches', { params }),
  create: (data: Record<string, unknown>) => request.post('/gsp/batches', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/gsp/batches/${id}`, data),
  remove: (id: number) => request.delete(`/gsp/batches/${id}`),
  expiring: (days = 180) => request.get('/gsp/batches/expiring', { params: { days } }),
}
