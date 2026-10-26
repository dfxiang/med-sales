<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

function goHome() {
  router.push(userStore.hasPermission('dashboard:view') ? '/dashboard' : '/403')
}
</script>

<template>
  <el-card data-test="forbidden">
    <el-result icon="warning" title="403" sub-title="当前账号没有访问该页面的权限">
      <template #extra>
        <div class="forbidden-tip">
          当前账号：<b>{{ userStore.username }}</b>
        </div>
        <div class="forbidden-tip">
          已获权限：{{ userStore.isSuperuser ? '全部权限' : userStore.permissions.length ? userStore.permissions.join('、') : '（暂无，请联系管理员分配角色）' }}
        </div>
        <el-button type="primary" data-test="btn-back-home" @click="goHome">返回可访问页面</el-button>
      </template>
    </el-result>
  </el-card>
</template>

<style scoped>
.forbidden-tip {
  color: var(--el-text-color-regular);
  font-size: 13px;
  margin-bottom: 8px;
  word-break: break-all;
}
</style>
