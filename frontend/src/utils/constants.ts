export const customerTypeOptions = [
  { label: '三级医院', value: '三级医院' },
  { label: '二级医院', value: '二级医院' },
  { label: '基层医疗机构', value: '基层医疗机构' },
  { label: '民营医院', value: '民营医院' },
  { label: '疾控中心', value: '疾控中心' },
  { label: '连锁药房', value: '连锁药房' },
  { label: '单体药房', value: '单体药房' },
  { label: '诊所', value: '诊所' },
  { label: '经销商', value: '经销商' },
  { label: '其他机构', value: '其他机构' },
]

export const coopLevelOptions = [
  { label: '战略合作', value: '战略合作' },
  { label: '重点客户', value: '重点客户' },
  { label: '普通客户', value: '普通客户' },
  { label: '新客户', value: '新客户' },
]

export const statusOptions = [
  { label: '正常', value: '正常' },
  { label: '冻结', value: '冻结' },
  { label: '流失', value: '流失' },
  { label: '暂停合作', value: '暂停合作' },
]

export const customerStatusOptions = statusOptions

export const supplierStatusOptions = [
  { label: '合作中', value: '合作中' },
  { label: '暂停合作', value: '暂停合作' },
  { label: '已终止', value: '已终止' },
]

export const warehouseStatusOptions = [
  { label: '正常', value: '正常' },
  { label: '停用', value: '停用' },
]

export const storageOptions = [
  { label: '常温', value: '常温' },
  { label: '阴凉', value: '阴凉' },
  { label: '冷藏 2~8℃', value: '冷藏 2~8℃' },
  { label: '冷冻', value: '冷冻' },
]

export const deliveryTypeOptions = [
  { label: '常温运输', value: '常温运输' },
  { label: '冷链运输', value: '冷链运输' },
  { label: '快递配送', value: '快递配送' },
  { label: '客户自提', value: '客户自提' },
]

export const invoiceTypeOptions = [
  { label: '增值税专用发票', value: '增值税专用发票' },
  { label: '增值税普通发票', value: '增值税普通发票' },
  { label: '不开发票', value: '不开发票' },
]

export const settlementOptions = [
  { label: '现款', value: '现款' },
  { label: '月结30天', value: '月结30天' },
  { label: '月结45天', value: '月结45天' },
  { label: '月结60天', value: '月结60天' },
  { label: '月结90天', value: '月结90天' },
]

export const paymentMethodOptions = [
  { label: '银行转账', value: '银行转账' },
  { label: '对公转账', value: '对公转账' },
  { label: '承兑汇票', value: '承兑汇票' },
  { label: '现金', value: '现金' },
  { label: '网上银行', value: '网上银行' },
]

export const returnReasonOptions = [
  { label: '质量问题', value: '质量问题' },
  { label: '效期临近', value: '效期临近' },
  { label: '冷链断链', value: '冷链断链' },
  { label: '发错货', value: '发错货' },
  { label: '滞销退货', value: '滞销退货' },
  { label: '医院退回', value: '医院退回' },
  { label: '部分商品退货', value: '部分商品退货' },
]

export const statusTagMap: Record<string, { text?: string; type?: 'success' | 'warning' | 'danger' | 'info' | 'primary' }> = {
  正常: { type: 'success' },
  冻结: { type: 'danger' },
  流失: { type: 'info' },
  暂停合作: { type: 'warning' },
  合作中: { type: 'success' },
  已终止: { type: 'danger' },
  停用: { type: 'danger' },
  待收货: { type: 'warning' },
  部分收货: { type: 'primary' },
  已完成: { type: 'success' },
  待付款: { type: 'warning' },
  已发货: { type: 'primary' },
  已取消: { type: 'info' },
  待处理: { type: 'warning' },
  成功: { type: 'success' },
  失败: { type: 'danger' },
  冲正: { type: 'warning' },
  在职: { type: 'success' },
  离职: { type: 'info' },
  有效: { type: 'success' },
  即将到期: { type: 'warning' },
  过期: { type: 'danger' },
}
