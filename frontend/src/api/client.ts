import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

export type Schemas = components['schemas']
export type StrategyConfig = Schemas['StrategyConfig']
export type IndicatorSpec = Schemas['IndicatorSpec']
export type Condition = Schemas['Condition']
export type Param = StrategyConfig['capital'] | Schemas['ValuesSpec'] | Schemas['RangeSpec']
export type Job = Schemas['JobOut']

export const api = createClient<paths>({ baseUrl: '' })

export class ApiError extends Error {}

type ErrorBody = { mensaje?: string; detail?: unknown; detalle?: unknown }

function describe(err: unknown): string {
  if (err && typeof err === 'object') {
    const e = err as ErrorBody
    if (typeof e.mensaje === 'string') {
      const det = Array.isArray(e.detalle)
        ? e.detalle
            .map((d: { loc?: unknown[]; msg?: string }) => `${(d.loc ?? []).join('.')}: ${d.msg ?? ''}`)
            .join(' · ')
        : ''
      return det ? `${e.mensaje} ${det}` : e.mensaje
    }
    if (e.detail) return JSON.stringify(e.detail)
  }
  return String(err)
}

/** Devuelve `data` o lanza un ApiError con el mensaje en español del backend. */
export function unwrap<T>(res: { data?: T; error?: unknown; response: Response }): T {
  if (res.error !== undefined || res.data === undefined) {
    throw new ApiError(describe(res.error ?? res.response.statusText))
  }
  return res.data
}
