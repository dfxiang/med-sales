import request from '@/utils/request'

export const inventoryApi = {
  list: (params: Record<string, unknown>) => request.get('/inventory', { params }),
  get: (id: number) => request.get(`/inventory/${id}`),
  movements: (params: Record<string, unknown>) => request.get('/inventory/movements', { params }),
  openStock: (data: Record<string, unknown>) => request.post('/inventory/open-stock', data),
}
