/// <reference types="vite/client" />

import 'vue'

declare module 'vue' {
  interface ComponentCustomProperties {
    /** 当前界面语言对应的 Intl locale，供模板格式化数字和日期。 */
    $intlLocale: () => string
  }
}
