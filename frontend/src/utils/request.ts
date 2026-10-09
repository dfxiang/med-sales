import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

export const baseURL: string = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api'

const request = axios.create({
  baseURL,
  timeout: 30_000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError<{ detail?: string }>) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      if (!location.pathname.startsWith('/login')) {
        location.href = '/login'
      }
    }
    // 网关（nginx）拒绝的超大请求体不会返回 JSON，单独给出可读提示
    if (error.response?.status === 413) {
      ElMessage.error('文件过大，超出服务器允许的上传体积（单文件上限 20MB）')
      return Promise.reject(error)
    }
    const detail = error.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '请求失败，请稍后重试')
    return Promise.reject(error)
  },
)

export default request
