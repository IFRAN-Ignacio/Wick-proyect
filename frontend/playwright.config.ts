import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 180_000,
  workers: 1,
  use: { baseURL: 'http://localhost:5173', viewport: { width: 1400, height: 900 } },
})
