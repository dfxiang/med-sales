<script setup lang="ts">
import { SUPPORTED_LOCALES, localeLabel, useAppPreferences, type AppLocale } from '@/i18n'

defineProps<{
  /** 登录页使用透明背景，主界面使用卡片表面色。 */
  variant?: 'plain' | 'surface'
}>()

const { locale, theme, setLocale, toggleTheme } = useAppPreferences()

function onLocaleCommand(command: string | number | object) {
  setLocale(String(command) as AppLocale)
}
</script>

<template>
  <div class="preference-controls" :class="`is-${variant || 'surface'}`" data-test="preference-controls">
    <el-dropdown trigger="click" @command="onLocaleCommand">
      <button class="preference-button" type="button" aria-label="切换语言" data-test="language-switcher">
        <span class="preference-code">{{ locale === 'zh-CN' ? '中' : locale.toUpperCase() }}</span>
        <span class="preference-name">{{ localeLabel(locale) }}</span>
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="item in SUPPORTED_LOCALES"
            :key="item.code"
            :command="item.code"
            :class="{ 'is-selected': locale === item.code }"
          >
            <span>{{ item.label }}</span>
            <span v-if="locale === item.code" class="preference-check" aria-hidden="true">✓</span>
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
    <button
      class="preference-button theme-toggle"
      type="button"
      aria-label="切换主题"
      :aria-pressed="theme === 'dark'"
      data-test="theme-toggle"
      @click="toggleTheme"
    >
      <span class="theme-symbol" :class="`is-${theme}`" aria-hidden="true"></span>
      <span>{{ theme === 'dark' ? '深色' : '浅色' }}</span>
    </button>
  </div>
</template>

<style scoped>
.preference-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}
.preference-button {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  color: var(--el-text-color-regular);
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease;
}
.preference-button:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}
.preference-button:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}
.is-plain .preference-button {
  border-color: rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  backdrop-filter: blur(10px);
}
.is-plain .preference-button:hover {
  border-color: rgba(255, 255, 255, 0.74);
  background: rgba(255, 255, 255, 0.22);
  color: #fff;
}
.preference-code {
  display: inline-grid;
  min-width: 18px;
  height: 18px;
  place-items: center;
  border-radius: 5px;
  background: var(--el-fill-color);
  font-size: 10px;
  font-weight: 700;
}
.is-plain .preference-code {
  background: rgba(255, 255, 255, 0.18);
}
.preference-name {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preference-check {
  margin-left: 20px;
  color: var(--el-color-primary);
  font-weight: 700;
}
.theme-symbol {
  position: relative;
  display: inline-block;
  width: 15px;
  height: 15px;
  border: 1.5px solid currentColor;
  border-radius: 50%;
}
.theme-symbol.is-light::after {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  content: "";
}
.theme-symbol.is-dark::after {
  position: absolute;
  right: -2px;
  bottom: 0;
  width: 5px;
  height: 5px;
  border: 1.5px solid currentColor;
  border-radius: 50%;
  content: "";
}
@media (max-width: 640px) {
  .preference-name {
    display: none;
  }
  .preference-button {
    min-height: 44px;
    min-width: 40px;
    justify-content: center;
    padding: 0 8px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .preference-button {
    transition: none;
  }
}
</style>
