import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  LineSeries,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { Schemas } from '@/api/client'
import { es } from '@/i18n/es'

type Detail = Schemas['VariantDetail']

const t = (ms: number) => Math.floor(ms / 1000) as UTCTimestamp
const OVERLAY_COLORS = ['#f59e0b', '#38bdf8', '#a78bfa', '#f472b6', '#34d399', '#fb7185']

function baseOptions(el: HTMLElement) {
  return {
    width: el.clientWidth,
    height: el.clientHeight,
    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#a1a1aa', attributionLogo: true },
    grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
    timeScale: { timeVisible: true, secondsVisible: false },
  }
}

export function CandleChart({ detail }: { detail: Detail }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const chart = createChart(el, baseOptions(el))
    const c = detail.candles
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#f43f5e',
    })
    series.setData(c.ts.map((ts, i) => ({ time: t(ts), open: c.open[i], high: c.high[i], low: c.low[i], close: c.close[i] })))
    detail.overlays.forEach((o, k) => {
      const line = chart.addSeries(LineSeries, {
        color: OVERLAY_COLORS[k % OVERLAY_COLORS.length],
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        title: o.name,
      })
      line.setData(
        o.values.flatMap((v, i) => (v === null ? [] : [{ time: t(c.ts[i]), value: v }])),
      )
    })
    const first = c.ts[0] ?? 0
    const markers: SeriesMarker<Time>[] = []
    for (const tr of detail.trades) {
      if (tr.entry_ts >= first)
        markers.push({ time: t(tr.entry_ts), position: 'belowBar', color: '#22d3ee', shape: 'arrowUp', text: es.result.markerBuy })
      if (tr.exit_ts >= first)
        markers.push({
          time: t(tr.exit_ts),
          position: 'aboveBar',
          color: tr.pnl_net >= 0 ? '#10b981' : '#f43f5e',
          shape: 'arrowDown',
          text: es.result.reasons[tr.reason] ?? tr.reason,
        })
    }
    markers.sort((a, b) => (a.time as number) - (b.time as number))
    createSeriesMarkers(series, markers)
    chart.timeScale().fitContent()
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }))
    ro.observe(el)
    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [detail])
  return <div ref={ref} className="h-[480px] w-full" />
}

export function EquityChart({ detail }: { detail: Detail }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const chart = createChart(el, baseOptions(el))
    const s = chart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2, priceLineVisible: false })
    s.setData(detail.equity.ts.map((ts, i) => ({ time: t(ts), value: detail.equity.values[i] })))
    chart.timeScale().fitContent()
    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth }))
    ro.observe(el)
    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [detail])
  return <div ref={ref} className="h-[260px] w-full" />
}
