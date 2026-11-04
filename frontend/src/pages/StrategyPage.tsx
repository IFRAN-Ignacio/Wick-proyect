import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { api, unwrap, type Condition, type IndicatorSpec, type Param, type StrategyConfig } from '@/api/client'
import { NativeSelect } from '@/components/NativeSelect'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { ParamInput } from '@/features/strategy-editor/ParamInput'
import { es } from '@/i18n/es'
import { useJob } from '@/lib/useJob'
import { TIMEFRAMES } from '@/pages/DataPage'

type IndType = IndicatorSpec['type']
type Op = Condition['op']

const IND_PARAMS: Record<IndType, Record<string, number>> = {
  sma: { length: 20 },
  ema: { length: 20 },
  rsi: { length: 14 },
  macd: { fast: 12, slow: 26, signal: 9 },
  bbands: { length: 20, mult: 2 },
  atr: { length: 14 },
}
const IND_OUTPUTS: Record<IndType, string[]> = {
  sma: [''],
  ema: [''],
  rsi: [''],
  macd: ['macd', 'signal', 'hist'],
  bbands: ['upper', 'middle', 'lower'],
  atr: [''],
}
const OPS: Op[] = ['crosses_above', 'crosses_below', '>', '<']
const PRICES = ['open', 'high', 'low', 'close'] as const

type Exit = NonNullable<StrategyConfig['exit']>

function fullExit(c: StrategyConfig): Exit {
  return {
    stop: c.exit?.stop ?? { type: 'none', pct: 2, atr_length: 14, mult: 2 },
    take_profit: c.exit?.take_profit ?? { type: 'none', pct: 4, ratio: 2 },
    on_opposite_signal: c.exit?.on_opposite_signal ?? false,
  }
}

// Borrador en memoria del módulo: sobrevive a cambiar de pantalla.
let draft: StrategyConfig | null = null

function operands(cfg: StrategyConfig): string[] {
  const out: string[] = [...PRICES]
  for (const ind of cfg.indicators ?? []) {
    for (const o of IND_OUTPUTS[ind.type]) out.push(o === '' ? ind.id : `${ind.id}.${o}`)
  }
  return out
}

function newIndicatorId(cfg: StrategyConfig, type: IndType): string {
  const ids = new Set((cfg.indicators ?? []).map((i) => i.id))
  let k = 1
  while (ids.has(`${type}${k}`)) k++
  return `${type}${k}`
}

export function StrategyPage() {
  const navigate = useNavigate()
  const templates = useQuery({
    queryKey: ['templates'],
    queryFn: async () => unwrap(await api.GET('/api/v1/templates')),
  })
  const saved = useQuery({
    queryKey: ['strategies'],
    queryFn: async () => unwrap(await api.GET('/api/v1/strategies')),
  })
  const [cfg, setCfgState] = useState<StrategyConfig | null>(draft)
  const [formKey, setFormKey] = useState(0)
  const [jobId, setJobId] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [savedMsg, setSavedMsg] = useState<string | null>(null)
  const job = useJob(jobId)

  function setCfg(next: StrategyConfig) {
    draft = next
    setCfgState(next)
  }
  function load(c: StrategyConfig) {
    setCfg(structuredClone(c))
    setFormKey((k) => k + 1) // reinicia los sub-formularios (no quedan campos viejos)
    setJobId(null)
    setRunError(null)
  }
  function edit(fn: (c: StrategyConfig) => void) {
    if (!cfg) return
    const c = structuredClone(cfg)
    fn(c)
    setCfg(c)
  }

  useEffect(() => {
    if (!cfg && templates.data?.[0]) load(templates.data[0].config)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templates.data])

  // Contador de variantes en vivo: preview del backend con debounce.
  const [previewCfg, setPreviewCfg] = useState<StrategyConfig | null>(null)
  useEffect(() => {
    const t = setTimeout(() => setPreviewCfg(cfg), 350)
    return () => clearTimeout(t)
  }, [cfg])
  const preview = useQuery({
    queryKey: ['preview', previewCfg],
    enabled: previewCfg !== null,
    queryFn: async () => unwrap(await api.POST('/api/v1/backtests/preview', { body: previewCfg! })),
    retry: false,
  })

  useEffect(() => {
    if (job?.status === 'done') {
      const id = (job.result as { backtest_id?: string }).backtest_id
      if (id) navigate(`/resultado/${id}`)
    }
  }, [job, navigate])

  async function run() {
    if (!cfg) return
    setRunError(null)
    try {
      const r = unwrap(await api.POST('/api/v1/backtests', { body: { config: cfg } }))
      setJobId(r.job_id)
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e))
    }
  }
  async function save() {
    if (!cfg) return
    try {
      unwrap(await api.POST('/api/v1/strategies', { body: { config: cfg } }))
      setSavedMsg(es.strategy.savedOk)
      void saved.refetch()
    } catch (e) {
      setSavedMsg(e instanceof Error ? e.message : String(e))
    }
  }

  if (!cfg) return <div>{es.app.loading}</div>
  const ops = operands(cfg)
  const stop = cfg.exit?.stop ?? { type: 'none', pct: 2, atr_length: 14, mult: 2 }
  const tp = cfg.exit?.take_profit ?? { type: 'none', pct: 4, ratio: 2 }
  const sizing = cfg.sizing ?? { mode: 'pct_capital', value: 100, compound: true }
  const costs = cfg.costs ?? { taker: 0.001, slippage: 0.0005 }
  const running = job?.status === 'running'
  const pv = preview.data

  const conditionsEditor = (side: 'long' | 'short') => {
    const rule = side === 'long' ? cfg.entry.long : cfg.entry.short
    const conds = rule?.conditions ?? []
    return (
      <div className="flex flex-col gap-2">
        {conds.map((c, i) => {
          const isNum = typeof c.right !== 'string'
          return (
            <div key={i} className="flex flex-wrap items-end gap-2">
              <NativeSelect
                value={c.left}
                onChange={(e) => edit((d) => void ((side === 'long' ? d.entry.long : d.entry.short!).conditions[i].left = e.target.value))}
              >
                {ops.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </NativeSelect>
              <NativeSelect
                value={c.op}
                onChange={(e) => edit((d) => void ((side === 'long' ? d.entry.long : d.entry.short!).conditions[i].op = e.target.value as Op))}
              >
                {OPS.map((o) => (
                  <option key={o} value={o}>
                    {es.strategy.ops[o]}
                  </option>
                ))}
              </NativeSelect>
              <NativeSelect
                value={isNum ? '__num' : (c.right as string)}
                onChange={(e) =>
                  edit((d) => {
                    const cc = (side === 'long' ? d.entry.long : d.entry.short!).conditions[i]
                    cc.right = e.target.value === '__num' ? { value: 50 } : e.target.value
                  })
                }
              >
                <option value="__num">{es.strategy.number}</option>
                {ops.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </NativeSelect>
              {isNum && (
                <ParamInput
                  key={`${formKey}-${side}-${i}`}
                  label={es.strategy.number}
                  value={(c.right as { value: Param }).value}
                  onChange={(p) =>
                    edit((d) => void ((side === 'long' ? d.entry.long : d.entry.short!).conditions[i].right = { value: p }))
                  }
                />
              )}
              <Button
                variant="ghost"
                size="sm"
                disabled={side === 'long' && conds.length === 1}
                onClick={() =>
                  edit((d) => {
                    const r = side === 'long' ? d.entry.long : d.entry.short!
                    r.conditions.splice(i, 1)
                    if (side === 'short' && r.conditions.length === 0) {
                      d.entry.short = null
                      if (d.exit) d.exit.on_opposite_signal = false
                    }
                  })
                }
              >
                {es.strategy.remove}
              </Button>
            </div>
          )
        })}
        <Button
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() =>
            edit((d) => {
              const c: Condition = { left: 'close', op: '>', right: { value: 0 } }
              if (side === 'long') d.entry.long.conditions.push(c)
              else d.entry.short = { conditions: [...(d.entry.short?.conditions ?? []), c] }
            })
          }
        >
          {es.strategy.addCondition}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 max-w-6xl" key={formKey}>
      <h1 className="text-2xl font-semibold">{es.strategy.title}</h1>

      <Card>
        <CardHeader>
          <CardTitle>{es.strategy.templates}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">{es.strategy.templateWarning}</p>
          {templates.data?.map((t) => (
            <div key={t.id} className="flex items-start justify-between gap-4 border-b border-border pb-2">
              <div>
                <div className="font-medium">{t.title}</div>
                <div className="text-xs text-muted-foreground">{t.description}</div>
              </div>
              <Button size="sm" onClick={() => load(t.config)}>
                {es.strategy.useTemplate}
              </Button>
            </div>
          ))}
          {saved.data && saved.data.length > 0 && (
            <div className="flex items-center gap-2 pt-2">
              <span className="text-sm">{es.strategy.saved}:</span>
              <NativeSelect
                defaultValue=""
                onChange={(e) => {
                  const s = saved.data.find((x) => x.id === e.target.value)
                  if (s) load(s.config)
                }}
              >
                <option value="">—</option>
                {saved.data.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.updated_at.slice(0, 16).replace('T', ' ')})
                  </option>
                ))}
              </NativeSelect>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{es.strategy.general}</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-3">
          <div>
            <Label>{es.strategy.name}</Label>
            <Input value={cfg.name} onChange={(e) => edit((d) => void (d.name = e.target.value))} />
          </div>
          <div>
            <Label>{es.strategy.symbol}</Label>
            <Input
              value={cfg.symbol}
              onChange={(e) => edit((d) => void (d.symbol = e.target.value.toUpperCase().trim()))}
            />
          </div>
          <div>
            <Label>{es.strategy.timeframe}</Label>
            <NativeSelect
              className="w-full"
              value={cfg.timeframe}
              onChange={(e) => edit((d) => void (d.timeframe = e.target.value as StrategyConfig['timeframe']))}
            >
              {TIMEFRAMES.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </NativeSelect>
          </div>
          <div>
            <Label>{es.strategy.from}</Label>
            <Input type="date" value={cfg.range.from} onChange={(e) => edit((d) => void (d.range.from = e.target.value))} />
          </div>
          <div>
            <Label>{es.strategy.to}</Label>
            <Input type="date" value={cfg.range.to} onChange={(e) => edit((d) => void (d.range.to = e.target.value))} />
          </div>
          <div>
            <Label>{es.strategy.capital}</Label>
            <Input
              type="number"
              value={String(cfg.capital)}
              onChange={(e) => edit((d) => void (d.capital = Number(e.target.value)))}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{es.strategy.indicators}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {(cfg.indicators ?? []).map((ind, i) => (
            <div key={i} className="flex flex-wrap items-end gap-3 border-b border-border pb-3">
              <div>
                <Label>{es.strategy.indicatorId}</Label>
                <Input
                  className="w-32"
                  value={ind.id}
                  onChange={(e) => edit((d) => void (d.indicators![i].id = e.target.value))}
                />
              </div>
              <div>
                <Label>{es.strategy.indicatorType}</Label>
                <NativeSelect
                  value={ind.type}
                  onChange={(e) =>
                    edit((d) => {
                      const type = e.target.value as IndType
                      // Al cambiar el tipo se limpian los parámetros viejos.
                      d.indicators![i] = { id: ind.id, type, params: { ...IND_PARAMS[type] }, source: ind.source }
                    })
                  }
                >
                  {(Object.keys(IND_PARAMS) as IndType[]).map((t) => (
                    <option key={t} value={t}>
                      {es.strategy.indicatorNames[t]}
                    </option>
                  ))}
                </NativeSelect>
              </div>
              {ind.type !== 'atr' && (
                <div>
                  <Label>{es.strategy.source}</Label>
                  <NativeSelect
                    value={ind.source ?? 'close'}
                    onChange={(e) => edit((d) => void (d.indicators![i].source = e.target.value as IndicatorSpec['source']))}
                  >
                    {PRICES.map((p) => (
                      <option key={p} value={p}>
                        {es.strategy.prices[p]}
                      </option>
                    ))}
                  </NativeSelect>
                </div>
              )}
              {Object.keys(IND_PARAMS[ind.type]).map((pname) => (
                <ParamInput
                  key={`${formKey}-${i}-${ind.type}-${pname}`}
                  label={es.strategy.paramNames[pname] ?? pname}
                  value={(ind.params?.[pname] as Param | undefined) ?? IND_PARAMS[ind.type][pname]}
                  onChange={(p) => edit((d) => void (d.indicators![i].params = { ...d.indicators![i].params, [pname]: p }))}
                />
              ))}
              <Button variant="ghost" size="sm" onClick={() => edit((d) => void d.indicators!.splice(i, 1))}>
                {es.strategy.remove}
              </Button>
            </div>
          ))}
          <Button
            variant="outline"
            size="sm"
            className="self-start"
            onClick={() =>
              edit((d) => {
                d.indicators = [
                  ...(d.indicators ?? []),
                  { id: newIndicatorId(d, 'ema'), type: 'ema', params: { length: 20 }, source: 'close' },
                ]
              })
            }
          >
            {es.strategy.addIndicator}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{es.strategy.entry}</CardTitle>
        </CardHeader>
        <CardContent>{conditionsEditor('long')}</CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{es.strategy.opposite}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">{es.strategy.oppositeHelp}</p>
          {conditionsEditor('short')}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{es.strategy.exits}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label>{es.strategy.stop}</Label>
              <NativeSelect
                value={stop.type}
                onChange={(e) =>
                  edit((d) => {
                    d.exit = { ...fullExit(d), stop: { ...stop, type: e.target.value as typeof stop.type } }
                    if (e.target.value === 'none' && d.exit.take_profit?.type === 'rr') d.exit.take_profit = { ...d.exit.take_profit, type: 'none' }
                  })
                }
              >
                <option value="none">{es.strategy.stopNone}</option>
                <option value="pct">{es.strategy.stopPct}</option>
                <option value="atr">{es.strategy.stopAtr}</option>
              </NativeSelect>
            </div>
            {stop.type === 'pct' && (
              <ParamInput
                key={`${formKey}-stoppct`}
                label={es.strategy.stopPctLabel}
                value={stop.pct ?? 2}
                onChange={(p) => edit((d) => void (d.exit = { ...fullExit(d), stop: { ...stop, pct: p } }))}
              />
            )}
            {stop.type === 'atr' && (
              <>
                <ParamInput
                  key={`${formKey}-atrlen`}
                  label={es.strategy.atrLength}
                  value={stop.atr_length ?? 14}
                  onChange={(p) => edit((d) => void (d.exit = { ...fullExit(d), stop: { ...stop, atr_length: p } }))}
                />
                <ParamInput
                  key={`${formKey}-atrmult`}
                  label={es.strategy.atrMult}
                  value={stop.mult ?? 2}
                  onChange={(p) => edit((d) => void (d.exit = { ...fullExit(d), stop: { ...stop, mult: p } }))}
                />
              </>
            )}
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label>{es.strategy.tp}</Label>
              <NativeSelect
                value={tp.type}
                onChange={(e) => edit((d) => void (d.exit = { ...fullExit(d), take_profit: { ...tp, type: e.target.value as typeof tp.type } }))}
              >
                <option value="none">{es.strategy.tpNone}</option>
                <option value="pct">{es.strategy.tpPct}</option>
                {stop.type !== 'none' && <option value="rr">{es.strategy.tpRr}</option>}
              </NativeSelect>
            </div>
            {tp.type === 'pct' && (
              <ParamInput
                key={`${formKey}-tppct`}
                label={es.strategy.tpPctLabel}
                value={tp.pct ?? 4}
                onChange={(p) => edit((d) => void (d.exit = { ...fullExit(d), take_profit: { ...tp, pct: p } }))}
              />
            )}
            {tp.type === 'rr' && (
              <ParamInput
                key={`${formKey}-tprr`}
                label={es.strategy.tpRatio}
                value={tp.ratio ?? 2}
                onChange={(p) => edit((d) => void (d.exit = { ...fullExit(d), take_profit: { ...tp, ratio: p } }))}
              />
            )}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={cfg.exit?.on_opposite_signal ?? false}
              disabled={!cfg.entry.short}
              onCheckedChange={(v) => edit((d) => void (d.exit = { ...fullExit(d), on_opposite_signal: v === true }))}
            />
            {es.strategy.exitOpposite}
          </label>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {es.strategy.sizing} · {es.strategy.costs}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <ParamInput
            key={`${formKey}-size`}
            label={es.strategy.sizingPct}
            value={sizing.value ?? 100}
            onChange={(p) => edit((d) => void (d.sizing = { ...sizing, value: p }))}
          />
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={sizing.compound ?? true}
              onCheckedChange={(v) => edit((d) => void (d.sizing = { ...sizing, compound: v === true }))}
            />
            {es.strategy.compound}
          </label>
          <div>
            <Label>{es.strategy.taker}</Label>
            <Input
              type="number"
              step="0.01"
              value={String(+((costs.taker ?? 0) * 100).toFixed(6))}
              onChange={(e) => edit((d) => void (d.costs = { ...costs, taker: Number(e.target.value) / 100 }))}
            />
          </div>
          <div>
            <Label>{es.strategy.slippage}</Label>
            <Input
              type="number"
              step="0.01"
              value={String(+((costs.slippage ?? 0) * 100).toFixed(6))}
              onChange={(e) => edit((d) => void (d.costs = { ...costs, slippage: Number(e.target.value) / 100 }))}
            />
          </div>
          <p className="text-xs text-muted-foreground w-full">{es.strategy.costsNote}</p>
        </CardContent>
      </Card>

      <Card className="sticky bottom-0 border-primary">
        <CardContent className="flex flex-col gap-2 pt-6">
          {preview.error && (
            <Alert variant="destructive">
              <AlertDescription>{preview.error.message}</AlertDescription>
            </Alert>
          )}
          {pv && (
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <span className="text-lg font-semibold">{es.strategy.variants(pv.n_valid)}</span>
              {pv.n_discarded > 0 && (
                <span className="text-amber-400" title={pv.discard_reasons.map((r) => `${r.reason} (${r.count})`).join('\n')}>
                  {es.strategy.variantsDiscarded(pv.n_discarded)}
                </span>
              )}
              {pv.data.available ? (
                <span className="text-muted-foreground">{es.strategy.dataOk(pv.data.rows)}</span>
              ) : (
                <span className="text-rose-400">
                  {es.strategy.noData} <Link className="underline" to="/datos">{es.strategy.goToData}</Link>
                </span>
              )}
            </div>
          )}
          {pv?.data.warnings.map((w) => (
            <div key={w} className="text-xs text-amber-400">
              {w}
            </div>
          ))}
          {pv && pv.n_valid > 1 && <div className="text-xs text-amber-400">{es.strategy.overfitPreview(pv.n_valid)}</div>}
          {pv?.over_cap && <div className="text-sm text-rose-400">{es.strategy.overCap(pv.max_variants)}</div>}
          <div className="flex gap-2">
            <Button
              onClick={run}
              disabled={running || !pv || pv.over_cap || !pv.data.available || pv.n_valid === 0 || preview.isError}
            >
              {running ? es.strategy.running : es.strategy.run}
            </Button>
            <Button variant="outline" onClick={save}>
              {es.strategy.save}
            </Button>
            {savedMsg && <span className="text-xs text-muted-foreground self-center">{savedMsg}</span>}
          </div>
          {job && (
            <div className="flex flex-col gap-1">
              <Progress value={job.total ? (100 * job.done) / job.total : 0} />
              <span className="text-xs">{es.strategy.progress(job.done, job.total)}</span>
              {job.error && <span className="text-sm text-rose-400">{job.error}</span>}
            </div>
          )}
          {runError && <div className="text-sm text-rose-400">{runError}</div>}
        </CardContent>
      </Card>
    </div>
  )
}
