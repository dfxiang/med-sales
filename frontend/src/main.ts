import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './styles.css'

import App from './App.vue'
import permission from './directives/permission'
import { installI18n, intlLocale } from './i18n'
import router from './router'

const app = createApp(App)
// 模板中的数字/日期格式化统一使用当前界面语言。
app.config.globalProperties.$intlLocale = intlLocale
app.use(createPinia())
app.use(router)
// v-permission：按权限编码隐藏无权限的菜单/按钮（后端仍会独立校验）
app.directive('permission', permission)
// table.showOverflowTooltip：所有表格单元格单行显示，超出列宽用省略号截断并悬停显示完整内容，
// 避免长文本把行高撑成多行（见 AGENTS.md「表格」约定）。
app.use(ElementPlus, { table: { showOverflowTooltip: true } })
installI18n()
app.mount('#app')
