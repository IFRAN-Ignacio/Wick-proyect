// E2E real: necesita backend (8765) y Vite (5173) levantados, y BTCUSDT 1h 2023-2025 descargado.
import { expect, test, type Page } from '@playwright/test'

function trackErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(`console: ${m.text()}`)
  })
  return errors
}

test('datos → plantilla → corrida simple → resultado', async ({ page }) => {
  const errors = trackErrors(page)
  await page.goto('/datos')
  await expect(page.getByText('BTCUSDT · 1h')).toBeVisible()
  await page.getByRole('button', { name: 'Descargar' }).click()
  await expect(page.getByText('Descarga terminada')).toBeVisible({ timeout: 60_000 })
  await expect(page.getByText('36 meses ya estaban descargados y no se volvieron a bajar.')).toBeVisible()

  await page.goto('/estrategia')
  await page.getByRole('button', { name: 'Usar' }).first().click()
  await expect(page.getByText('1 variante', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Correr backtest' }).click()
  await expect(page).toHaveURL(/\/resultado\//, { timeout: 60_000 })
  await expect(page.getByText('Resultado sobre datos pasados. No garantiza resultados futuros.')).toBeVisible()
  await expect(page.getByText('Retorno total')).toBeVisible({ timeout: 30_000 })
  await expect(page.locator('canvas').first()).toBeVisible()
  await page.screenshot({ path: 'e2e-out/resultado-simple.png', fullPage: true })
  await page.getByRole('tab', { name: 'Desglose mensual' }).click()
  await expect(page.getByRole('cell', { name: '2023-01' })).toBeVisible()
  await page.getByRole('tab', { name: 'Trades' }).click()
  await expect(page.getByRole('cell', { name: 'Fin del período' }).or(page.getByRole('cell', { name: 'Stop' }).first())).toBeVisible()
  expect(errors).toEqual([])
})

test('multi-variante 3 × 2 × 2 = 12 → tabla de variantes', async ({ page }) => {
  const errors = trackErrors(page)
  await page.goto('/estrategia')
  await page.getByRole('button', { name: 'Usar' }).first().click()
  await expect(page.getByText('1 variante', { exact: true })).toBeVisible()
  const lists = page.getByRole('button', { name: 'lista', exact: true })
  const setList = async (n: number, text: string) => {
    await lists.nth(n).click()
    await page.getByPlaceholder('ej.: 10, 20, 30').nth(n).fill(text)
  }
  await setList(0, '10, 20, 30')
  await expect(page.getByText('3 variantes', { exact: true })).toBeVisible()
  await setList(1, '50, 100')
  await expect(page.getByText('6 variantes', { exact: true })).toBeVisible()
  await setList(2, '2, 4')
  await expect(page.getByText('12 variantes', { exact: true })).toBeVisible()
  await expect(page.getByText(/Vas a probar 12 variantes/)).toBeVisible()
  await page.getByRole('button', { name: 'Correr backtest' }).click()
  await expect(page).toHaveURL(/\/resultado\//, { timeout: 120_000 })
  await expect(page.getByText('Variantes', { exact: true })).toBeVisible()
  const rows = page.locator('table').first().locator('tbody tr')
  await expect(rows).toHaveCount(12)
  await expect(page.getByText(/Probaste 12 variantes/)).toBeVisible({ timeout: 30_000 })
  await page.getByRole('columnheader', { name: /Trades/ }).first().click()
  await rows.nth(3).click()
  await expect(page.getByText(/Variante: /)).toBeVisible()
  await page.screenshot({ path: 'e2e-out/resultado-multi.png', fullPage: true })
  expect(errors).toEqual([])
})

test('historial, configuración y panel del bot', async ({ page }) => {
  const errors = trackErrors(page)
  await page.goto('/historial')
  await expect(page.getByRole('link', { name: 'Abrir' }).first()).toBeVisible()
  await page.goto('/configuracion')
  await expect(page.getByText('API key de Google AI Studio (Gemini)')).toBeVisible()
  await page.getByRole('button', { name: 'Asistente' }).click()
  await expect(page.getByText('Asistente WICK')).toBeVisible()
  await page.screenshot({ path: 'e2e-out/bot.png', fullPage: true })
  expect(errors).toEqual([])
})
