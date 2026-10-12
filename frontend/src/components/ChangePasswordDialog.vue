<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { useUserStore } from '@/stores/user'

const visible = defineModel<boolean>({ required: true })

const userStore = useUserStore()
const saving = ref(false)
const form = ref({ old_password: '', new_password: '', confirm_password: '' })

watch(visible, (open) => {
  if (open) form.value = { old_password: '', new_password: '', confirm_password: '' }
})

async function onSubmit() {
  const { old_password, new_password, confirm_password } = form.value
  if (!old_password || !new_password || !confirm_password) {
    ElMessage.warning('请填写原密码与新密码')
    return
  }
  if (new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (new_password !== confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (new_password === old_password) {
    ElMessage.warning('新密码不能与原密码相同')
    return
  }
  saving.value = true
  try {
    await userStore.changePassword(form.value)
    ElMessage.success('密码已修改')
    visible.value = false
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="修改密码" width="460px" data-test="password-dialog">
    <el-form :model="form" label-width="100px">
      <el-form-item label="原密码" required>
        <el-input v-model="form.old_password" type="password" show-password data-test="password-old" />
      </el-form-item>
      <el-form-item label="新密码" required>
        <el-input v-model="form.new_password" type="password" show-password data-test="password-new" />
      </el-form-item>
      <el-form-item label="确认新密码" required>
        <el-input v-model="form.confirm_password" type="password" show-password data-test="password-confirm" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" data-test="password-save" @click="onSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>
