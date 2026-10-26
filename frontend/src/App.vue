<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'

import { elementLocale } from '@/i18n/element'
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>
