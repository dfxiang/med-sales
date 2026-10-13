<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import UserAvatar from '@/components/UserAvatar.vue'
import { useUserStore } from '@/stores/user'
import { AVATAR_ACCEPT, avatarSrc, validateAvatarFile } from '@/utils/avatar'

const visible = defineModel<boolean>({ required: true })

const userStore = useUserStore()
const saving = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
/** 本地预览地址（选中文件后立即显示，上传完成后清空并改用服务端头像） */
const preview = ref('')
const form = ref({ username: '', display_name: '', phone: '', email: '' })

const avatarImage = computed(() => preview.value || avatarSrc(userStore.avatarUrl))

watch(visible, (open) => {
  if (!open) return
  const info = userStore.userInfo
  form.value = {
    username: info?.username || userStore.username,
    display_name: info?.display_name || '',
    phone: info?.phone || '',
    email: info?.email || '',
  }
  preview.value = ''
})

async function onSave() {
  if (!form.value.display_name.trim()) {
    ElMessage.warning('请填写显示名称')
    return
  }
  saving.value = true
  try {
    await userStore.updateProfile({
      display_name: form.value.display_name.trim(),
      phone: form.value.phone.trim(),
      email: form.value.email.trim(),
    })
    ElMessage.success('个人资料已更新')
    visible.value = false
  } finally {
    saving.value = false
  }
}

function pickAvatar() {
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = '' // 允许重复选择同一个文件
  if (!file) return
  const error = validateAvatarFile(file)
  if (error) {
    ElMessage.warning(error)
    return
  }
  preview.value = URL.createObjectURL(file)
  uploading.value = true
  try {
    await userStore.uploadAvatar(file)
    ElMessage.success('头像已更新')
    preview.value = ''
  } finally {
    uploading.value = false
  }
}

async function onRemoveAvatar() {
  uploading.value = true
  try {
    await userStore.removeAvatar()
    preview.value = ''
    ElMessage.success('已恢复默认头像')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="个人资料" width="520px" data-test="profile-dialog">
    <div class="avatar-row">
      <!-- 头像不参与压缩：否则会被右侧操作区挤扁成椭圆 -->
      <UserAvatar
        class="preview-avatar"
        :src="avatarImage"
        :size="72"
        :name="form.display_name || form.username"
        data-test="avatar-preview"
      />
      <div class="avatar-actions">
        <el-button size="small" :loading="uploading" data-test="avatar-upload" @click="pickAvatar">
          上传头像
        </el-button>
        <el-button size="small" :loading="uploading" data-test="avatar-remove" @click="onRemoveAvatar">
          恢复默认
        </el-button>
        <div class="avatar-tip">支持 jpg / png / bmp / webp / gif，不超过 1MB，保存后统一为 256×256</div>
      </div>
      <input
        ref="fileInput"
        class="hidden-input"
        type="file"
        :accept="AVATAR_ACCEPT"
        data-test="avatar-input"
        @change="onFileChange"
      />
    </div>
    <el-form :model="form" label-width="90px">
      <el-form-item label="用户名">
        <el-input :model-value="form.username" disabled data-test="profile-username" />
      </el-form-item>
      <el-form-item label="显示名称" required>
        <el-input v-model="form.display_name" placeholder="请输入显示名称" data-test="profile-display-name" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.phone" placeholder="选填" data-test="profile-phone" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="选填" data-test="profile-email" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" data-test="profile-save" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.avatar-row {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;
  padding-left: 8px;
}
.avatar-actions {
  display: flex;
  flex: 1 1 auto;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.preview-avatar {
  flex: none;
}
.avatar-tip {
  width: 100%;
  color: #909399;
  font-size: 12px;
}
.hidden-input {
  display: none;
}
</style>
