import { defineConfig, devices } from '@playwright/test'

/**
 * 针对「已部署运行环境」的 Playwright 配置（不启动自带后端/前端）。
 *
 * 用法：
 *   cd frontend
 *   npx playwright test --config playwright.live.config.ts
 *   # 或指定地址：
 *   LIVE_BASE_URL=http://192.168.20.191:8088 npx playwright test --config playwright.live.config.ts
 */
export default defineConfig({
  testDir: './tests/live',
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.LIVE_BASE_URL || 'http://127.0.0.1:8088',
    testIdAttribute: 'data-test',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
