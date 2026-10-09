<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import GspAttachmentDrawer from '@/components/GspAttachmentDrawer.vue'
import {
  certificateApi,
  type Certificate,
  type Qualification,
} from '@/api/gsp'
import { certStatusTagMap, certTypeOptions, entityTypeOptions } from '@/utils/constants'
import { searchEntityOptions, type EntityOption } from '@/utils/gsp'

const entityType = ref('customer')
const entityId = ref<number | ''>('')
const entityOptions = ref<EntityOption[]>([])
const entityLoading = ref(false)
const entityLabel = ref('')

const qualification = ref<Qualification | null>(null)
const rows = ref<Certificate[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

const filesVisible = ref(false)
const currentCert = ref<Certificate | null>(null)

const createVisible = ref(false)
const createSaving = ref(false)
const createForm = reactive<Record<string, unknown>>({
  cert_type: '',
  cert_no: '',
  valid_from: '',
  valid_to: '',
  remark: '',
})

async function searchEntities(keyword: string) {
  entityLoading.value = true
  try {
    entityOptions.value = await searchEntityOptions(entityType.value, keyword)
  } finally {
    entityLoading.value = false
  }
}

async function onEntityTypeChange() {
  entityId.value = ''
  entityLabel.value = ''
  qualification.value = null
  rows.value = []
  total.value = 0
  await searchEntities('')
}

async function onEntityChange(value: number | '') {
  if (value === '' || value === null) return
  page.value = 1
  await load()
}

async function load() {
  if (entityId.value === '') {
    qualification.value = null
    rows.value = []
    total.value = 0
    return
  }
  loading.value = true
  try {
    const [profile, list] = await Promise.all([
      certificateApi.qualification(entityType.value, Number(entityId.value)) as Promise<Qualification>,
      certificateApi.list({
        entity_type: entityType.value,
        entity_id: entityId.value,
        page: page.value,
        size: size.value,
      }) as Promise<{ items: Certificate[]; total: number }>,
    ])
    qualification.value = profile
    entityLabel.value = profile.entity_name ?? ''
    rows.value = list.items
    total.value = list.total
  } finally {
    loading.value = false
  }
}

function onSizeChange() {
  page.value = 1
  load()
}

async function approve(row: Certificate) {
  const { value } = await ElMessageBox.prompt(
    `确认通过「${row.cert_type}」的首营资料审核？`,
    '审核通过',
    { inputPlaceholder: '审核意见（选填）', confirmButtonText: '通过' },
  )
  await certificateApi.review(row.id, 'approve', value || undefined)
  ElMessage.success('已通过审核')
  await load()
}

async function reject(row: Certificate) {
  const { value } = await ElMessageBox.prompt(
    `请填写「${row.cert_type}」的驳回原因`,
    '驳回',
    {
      inputPlaceholder: '驳回原因（必填）',
      inputValidator: (text: string) => (text ? true : '请填写驳回原因'),
      confirmButtonText: '驳回',
    },
  )
  await certificateApi.review(row.id, 'reject', value)
  ElMessage.success('已驳回')
  await load()
}

function openFiles(row: Certificate) {
  currentCert.value = row
  filesVisible.value = true
}

function openCreate() {
  for (const key of Object.keys(createForm)) createForm[key] = ''
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.cert_type) {
    ElMessage.warning('请填写证照类型')
    return
  }
  createSaving.value = true
  try {
    const payload: Record<string, unknown> = {
      entity_type: entityType.value,
      entity_id: Number(entityId.value),
      cert_type: createForm.cert_type,
    }
    for (const key of ['cert_no', 'valid_from', 'valid_to', 'remark']) {
      if (createForm[key]) payload[key] = createForm[key]
    }
    await certificateApi.create(payload)
    ElMessage.success('证照已提交，等待审核')
    createVisible.value = false
    await load()
  } finally {
    createSaving.value = false
  }
}

onMounted(async () => {
  const query = new URLSearchParams(window.location.search)
  const type = query.get('entity_type')
  const id = query.get('entity_id')
  if (type && entityTypeOptions.some((opt) => opt.value === type)) {
    entityType.value = type
  }
  await searchEntities('')
  if (id) {
    entityId.value = Number(id)
    await load()
  }
})
</script>

<template>
  <el-card>
    <div class="page-toolbar">
      <el-form :inline="true" class="search-form">
        <el-form-item label="对象类型">
          <el-select
            v-model="entityType"
            style="width: 160px"
            data-test="qual-entity-type"
            @change="onEntityTypeChange"
          >
            <el-option
              v-for="opt in entityTypeOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关联对象">
          <el-select
            v-model="entityId"
            filterable
            remote
            reserve-keyword
            :remote-method="searchEntities"
            :loading="entityLoading"
            placeholder="输入名称/编码搜索"
            style="width: 260px"
            data-test="qual-entity"
            @change="onEntityChange"
          >
            <el-option
              v-for="opt in entityOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="page-toolbar-actions">
        <el-button
          type="primary"
          :disabled="entityId === ''"
          data-test="qual-add-cert"
          @click="openCreate"
        >
          新增证照
        </el-button>
      </div>
    </div>

    <el-empty v-if="entityId === ''" description="请选择要查看的对象，查看其一户一档资质" />

    <template v-else>
      <el-alert
        v-if="qualification"
        :type="qualification.compliant ? 'success' : 'error'"
        :closable="false"
        show-icon
        data-test="qual-status"
        class="status-banner"
      >
        <template #title>
          {{ entityLabel }} · 资质档案
          <span v-if="!qualification.has_profile" class="muted">（尚未建档，暂不纳入交易管控）</span>
          <span v-else-if="qualification.compliant" class="muted">（资质合规，允许交易）</span>
          <span v-else class="muted">（资质不合规，交易已被阻断）</span>
        </template>
        <ul v-if="qualification.blocking.length" class="issue-list">
          <li v-for="issue in qualification.blocking" :key="`b-${issue.cert_id}-${issue.kind}`">
            阻断：{{ issue.detail }}
          </li>
        </ul>
        <ul v-if="qualification.warnings.length" class="issue-list">
          <li v-for="issue in qualification.warnings" :key="`w-${issue.cert_id}-${issue.kind}`">
            预警：{{ issue.detail }}
          </li>
        </ul>
      </el-alert>

      <el-table v-loading="loading" :data="rows" border stripe data-test="qual-table">
        <el-table-column prop="cert_type" label="证照类型" width="180" />
        <el-table-column prop="cert_no" label="证照编号" width="180" />
        <el-table-column prop="valid_from" label="生效日期" width="120" />
        <el-table-column prop="valid_to" label="到期日期" width="120" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="certStatusTagMap[row.effective_status]?.type || 'info'">
              {{ row.effective_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="review_status" label="审核" width="100" />
        <el-table-column prop="attachment_count" label="扫描件" width="90" />
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.review_status === '待审核'"
              link
              type="success"
              data-test="qual-approve"
              @click="approve(row)"
            >
              通过
            </el-button>
            <el-button
              v-if="row.review_status === '待审核'"
              link
              type="warning"
              data-test="qual-reject"
              @click="reject(row)"
            >
              驳回
            </el-button>
            <el-button link type="primary" data-test="qual-files" @click="openFiles(row)">
              扫描件
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        class="pagination"
        @current-change="load"
        @size-change="onSizeChange"
      />
    </template>
  </el-card>

  <GspAttachmentDrawer v-model="filesVisible" :certificate="currentCert" @changed="load" />

  <el-dialog
    v-model="createVisible"
    title="新增证照"
    width="560px"
    destroy-on-close
    data-test="qual-create-dialog"
  >
    <el-form :model="createForm" label-width="110px">
      <el-form-item label="证照类型" required>
        <el-select
          v-model="createForm.cert_type"
          filterable
          allow-create
          default-first-option
          placeholder="请选择或输入证照类型"
          style="width: 100%"
          data-test="qual-create-type"
        >
          <el-option
            v-for="opt in certTypeOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="证照编号">
        <el-input v-model="createForm.cert_no" data-test="qual-create-no" />
      </el-form-item>
      <el-form-item label="生效日期">
        <el-date-picker
          v-model="createForm.valid_from"
          type="date"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          data-test="qual-create-from"
        />
      </el-form-item>
      <el-form-item label="到期日期">
        <el-date-picker
          v-model="createForm.valid_to"
          type="date"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          data-test="qual-create-to"
        />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="createForm.remark" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="createSaving"
        data-test="qual-create-save"
        @click="submitCreate"
      >
        保存
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.status-banner {
  margin-bottom: 16px;
}
.issue-list {
  margin: 6px 0 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.7;
}
.muted {
  color: #909399;
  font-weight: 400;
}
.pagination {
  margin-top: 16px;
  justify-content: flex-start;
}
</style>
