import { computed } from 'vue'
import de from 'element-plus/es/locale/lang/de'
import en from 'element-plus/es/locale/lang/en'
import fr from 'element-plus/es/locale/lang/fr'
import id from 'element-plus/es/locale/lang/id'
import ms from 'element-plus/es/locale/lang/ms'
import vi from 'element-plus/es/locale/lang/vi'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import { appLocale } from './index'

const elementLocales = { 'zh-CN': zhCn, en, vi, ms, id, de, fr }

export const elementLocale = computed(() => elementLocales[appLocale.value])
