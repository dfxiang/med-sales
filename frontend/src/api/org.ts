import request from '@/utils/request'

export const departmentApi = {
  list: (params: Record<string, unknown>) => request.get('/departments', { params }),
  create: (data: Record<string, unknown>) => request.post('/departments', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/departments/${id}`, data),
  remove: (id: number) => request.delete(`/departments/${id}`),
}

export const employeeApi = {
  list: (params: Record<string, unknown>) => request.get('/employees', { params }),
  create: (data: Record<string, unknown>) => request.post('/employees', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/employees/${id}`, data),
  remove: (id: number) => request.delete(`/employees/${id}`),
}
