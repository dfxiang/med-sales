import { baseURL } from '@/utils/request'

/** 默认头像文件名（与后端 app/services/avatar.py 保持一致） */
export const DEFAULT_AVATAR = 'default.png'

/**
 * 头像地址拼接：后端返回的是 `/api/avatars/xxx.png` 这类相对路径，
 * 而前端在 dev/e2e 下直连后端源（绝对地址）、生产走 nginx 同源反代（`/api`）。
 * 统一按 baseURL + 文件名拼接，避免硬编码域名或重复 `/api` 前缀。
 */
export function avatarSrc(avatarUrl?: string | null): string {
  const filename = (avatarUrl || DEFAULT_AVATAR).split('/').pop() || DEFAULT_AVATAR
  return `${baseURL.replace(/\/$/, '')}/avatars/${filename}`
}

/** 允许上传的头像格式与大小（服务端仍会独立校验，这里只是提前反馈） */
export const AVATAR_ACCEPT = '.jpg,.jpeg,.png,.bmp,.webp,.gif'
export const AVATAR_MAX_BYTES = 1024 * 1024
export const AVATAR_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/bmp',
  'image/x-ms-bmp',
  'image/webp',
  'image/gif',
]

/** 客户端预校验：返回错误提示；通过则返回 null */
export function validateAvatarFile(file: File): string | null {
  if (file.type && !AVATAR_MIME_TYPES.includes(file.type)) {
    return '不支持的图片格式（支持 jpg/png/bmp/webp/gif）'
  }
  if (file.size > AVATAR_MAX_BYTES) {
    return '头像文件过大（上限 1MB）'
  }
  if (file.size === 0) {
    return '头像文件为空'
  }
  return null
}
