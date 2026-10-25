import { defineConfig, devices } from '@playwright/test'

/**
 * medapp 本地移动界面回归：静态服务打包进 APK 的 www 资源，接口连接运行中的 8001。
 * 这不是运行中 Web 部署的回归，因此与 playwright.live.config.ts 分开。
 */
export default defineConfig({
  testDir: './tests/android',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8097',
    testIdAttribute: 'data-test',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command:
      'python3 -m http.server 8097 --bind 127.0.0.1 --directory ../android/app/src/main/assets/www',
    url: 'http://127.0.0.1:8097',
    reuseExistingServer: true,
    timeout: 30_000,
  },
  projects: [{ name: 'pixel-7', use: { ...devices['Pixel 7'] } }],
})
