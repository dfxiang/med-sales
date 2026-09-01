import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5273',
    testIdAttribute: 'data-test',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'bash ../api/scripts/e2e_backend.sh',
      url: 'http://127.0.0.1:8002/',
      reuseExistingServer: false,
      timeout: 90_000,
    },
    {
      command: 'npm run dev -- --mode e2e --port 5273 --strictPort',
      url: 'http://127.0.0.1:5273',
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
