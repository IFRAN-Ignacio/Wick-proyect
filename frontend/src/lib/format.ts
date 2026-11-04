// Formato para mostrar. El backend trabaja en ms UTC y float64; se redondea solo acá.

const nf = (digits: number) =>
  new Intl.NumberFormat('es-AR', { minimumFractionDigits: digits, maximumFractionDigits: digits })

export function pct(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || !Number.isFinite(x)) return '—'
  return `${nf(digits).format(x * 100)} %`
}

export function num(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || !Number.isFinite(x)) return '—'
  return nf(digits).format(x)
}

export function price(x: number): string {
  const digits = x >= 1000 ? 2 : x >= 1 ? 4 : 8
  return nf(digits).format(x)
}

export function qty(x: number): string {
  return new Intl.NumberFormat('es-AR', { maximumFractionDigits: 8 }).format(x)
}

export function dateUtc(ts: number | null | undefined, withTime = true): string {
  if (ts === null || ts === undefined) return '—'
  const iso = new Date(ts).toISOString()
  return withTime ? `${iso.slice(0, 10)} ${iso.slice(11, 16)}` : iso.slice(0, 10)
}

export function bytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${nf(1).format(n / 1024)} KB`
  return `${nf(1).format(n / 1024 / 1024)} MB`
}

export function signClass(x: number | null | undefined): string {
  if (x === null || x === undefined || x === 0) return ''
  return x > 0 ? 'text-emerald-400' : 'text-rose-400'
}
