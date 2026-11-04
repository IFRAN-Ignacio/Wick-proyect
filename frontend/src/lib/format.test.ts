import { describe, expect, it } from 'vitest'
import { dateUtc, pct } from './format'

describe('format', () => {
  it('porcentaje con coma decimal y guion para null', () => {
    expect(pct(0.1234)).toBe('12,34 %')
    expect(pct(null)).toBe('—')
  })
  it('fechas siempre en UTC', () => {
    expect(dateUtc(1735689600000)).toBe('2025-01-01 00:00')
  })
})
