import request from '@/utils/request'

export interface CertificateAttachment {
  id: number
  certificate_id: number
  file_name: string
  content_type: string | null
  size: number
  uploaded_by: number | null
  version: number
  is_current: boolean
  /** 预览形态：pdf / image / other */
  kind: 'pdf' | 'image' | 'other'
  media_type: string
  /** 浏览器能否原生渲染（PDF / JPG / PNG 等） */
  previewable: boolean
  created_at: string
}

export interface Certificate {
  id: number
  entity_type: string
  entity_id: number
  entity_name: string | null
  cert_type: string
  cert_no: string | null
  valid_from: string | null
  valid_to: string | null
  status: string
  remark: string | null
  review_status: string
  reviewed_by: number | null
  review_remark: string | null
  reviewed_at: string | null
  effective_status: string
  days_to_expiry: number | null
  attachment_count: number
  created_at: string
}

export interface QualificationIssue {
  cert_id: number | null
  cert_type: string
  kind: string
  detail: string
}

export interface Qualification {
  entity_type: string
  entity_id: number
  entity_name: string | null
  has_profile: boolean
  compliant: boolean
  blocking: QualificationIssue[]
  warnings: QualificationIssue[]
  certificates: Certificate[]
}

export interface GspAlert {
  category: 'certificate' | 'batch'
  ref_id: number
  title: string
  subject: string
  entity_type: string | null
  entity_id: number | null
  valid_to: string | null
  days_left: number
  level: string
}

export interface GspAlertSummary {
  expired: number
  within_30: number
  within_60: number
  within_90: number
  pending_review: number
  certificate_total: number
  batch_total: number
}

export const certificateApi = {
  list: (params: Record<string, unknown>) => request.get('/gsp/certificates', { params }),
  create: (data: Record<string, unknown>) => request.post('/gsp/certificates', data),
  update: (id: number, data: Record<string, unknown>) =>
    request.put(`/gsp/certificates/${id}`, data),
  remove: (id: number) => request.delete(`/gsp/certificates/${id}`),
  expiring: (days = 90) => request.get('/gsp/certificates/expiring', { params: { days } }),
  /** 首营资料审核：approve=通过，reject=驳回 */
  review: (id: number, action: 'approve' | 'reject', remark?: string) =>
    request.post(`/gsp/certificates/${id}/review`, { action, remark }),
  qualification: (entityType: string, entityId: number) =>
    request.get(`/gsp/qualification/${entityType}/${entityId}`),
  attachments: (id: number, includeHistory = false) =>
    request.get(`/gsp/certificates/${id}/attachments`, {
      params: { include_history: includeHistory },
    }),
  uploadAttachment: (id: number, form: FormData) =>
    request.post(`/gsp/certificates/${id}/attachments`, form),
  downloadAttachment: (attachmentId: number) =>
    request.get(`/gsp/attachments/${attachmentId}/download`, { responseType: 'blob' }),
  /** 在线预览：接口以 inline 方式回传 S3 对象，前端直接用浏览器能力渲染 */
  previewAttachment: (attachmentId: number) =>
    request.get(`/gsp/attachments/${attachmentId}/preview`, { responseType: 'blob' }),
  removeAttachment: (attachmentId: number) => request.delete(`/gsp/attachments/${attachmentId}`),
}

export const batchApi = {
  list: (params: Record<string, unknown>) => request.get('/gsp/batches', { params }),
  create: (data: Record<string, unknown>) => request.post('/gsp/batches', data),
  update: (id: number, data: Record<string, unknown>) => request.put(`/gsp/batches/${id}`, data),
  remove: (id: number) => request.delete(`/gsp/batches/${id}`),
  expiring: (days = 180) => request.get('/gsp/batches/expiring', { params: { days } }),
}

export const alertApi = {
  list: (params: Record<string, unknown>) => request.get('/gsp/alerts', { params }),
  summary: () => request.get('/gsp/alerts/summary'),
}
