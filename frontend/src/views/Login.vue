<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import PreferenceControls from '@/components/PreferenceControls.vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const route = useRoute()

const form = ref({ username: 'admin', password: '' })
const loading = ref(false)

async function onSubmit() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.value.username, form.value.password)
    router.push((route.query.redirect as string) || '/dashboard')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-preferences">
      <PreferenceControls variant="plain" />
    </div>
    <el-card class="login-card">
      <h1 class="login-title">医药销售管理系统</h1>
      <p class="login-subtitle">药品 · 疫苗 · 医疗器械销售管理</p>
      <el-form :model="form" label-width="0" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" data-test="username" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            data-test="password"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-button"
          :loading="loading"
          data-test="login-submit"
          @click="onSubmit"
        >
          登 录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f6feb 0%, #3aa0ff 100%);
}
.login-preferences {
  position: absolute;
  top: 20px;
  right: 24px;
}
.login-card {
  width: 380px;
  padding: 12px 8px;
}
.login-title {
  text-align: center;
  margin: 4px 0 2px;
  font-size: 22px;
}
.login-subtitle {
  text-align: center;
  color: var(--el-text-color-secondary);
  margin: 0 0 20px;
  font-size: 13px;
}
.login-button {
  width: 100%;
}
@media (max-width: 640px) {
  .login-preferences {
    top: 12px;
    right: 12px;
  }
  .login-card {
    width: calc(100vw - 32px);
  }
}
</style>
