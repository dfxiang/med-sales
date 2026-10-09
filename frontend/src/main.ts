import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './styles.css'

import App from './App.vue'
import permission from './directives/permission'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
// v-permission：按权限编码隐藏无权限的菜单/按钮（后端仍会独立校验）
app.directive('permission', permission)
// table.showOverflowTooltip：所有表格单元格单行显示，超出列宽用省略号截断并悬停显示完整内容，
// 避免长文本把行高撑成多行（见 AGENTS.md「表格」约定）。
app.use(ElementPlus, { locale: zhCn, table: { showOverflowTooltip: true } })
app.mount('#app')
