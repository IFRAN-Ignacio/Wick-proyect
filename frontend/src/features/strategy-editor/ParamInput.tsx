import { useState } from 'react'
import type { Param } from '@/api/client'
import { Input } from '@/components/ui/input'
import { es } from '@/i18n/es'

type Mode = 'value' | 'list' | 'range'

function modeOf(p: Param): Mode {
  if (typeof p === 'number') return 'value'
  return 'values' in p ? 'list' : 'range'
}

function firstOf(p: Param): number {
  if (typeof p === 'number') return p
  return 'values' in p ? (p.values[0] ?? 0) : p.range[0]
}

/** Un parámetro numérico con modo valor / lista / rango (desde, hasta, paso). */
export function ParamInput({
  label,
  value,
  onChange,
}: {
  label: string
  value: Param
  onChange: (p: Param) => void
}) {
  const mode = modeOf(value)
  const [listText, setListText] = useState(
    typeof value === 'object' && 'values' in value ? value.values.join(', ') : '',
  )

  function setMode(m: Mode) {
    const v = firstOf(value)
    if (m === 'value') onChange(v)
    if (m === 'list') {
      setListText(String(v))
      onChange({ values: [v] })
    }
    if (m === 'range') onChange({ range: [v, v, 1] })
  }

  return (
    <div className="flex flex-col gap-1 min-w-40">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground">{label}</span>
        <div className="flex text-[10px] border border-border rounded overflow-hidden">
          {(['value', 'list', 'range'] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-1.5 py-0.5 ${m === mode ? 'bg-primary text-primary-foreground' : ''}`}
            >
              {m === 'value' ? es.strategy.modeValue : m === 'list' ? es.strategy.modeList : es.strategy.modeRange}
            </button>
          ))}
        </div>
      </div>
      {mode === 'value' && (
        <Input
          type="number"
          step="any"
          value={String(value)}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      )}
      {mode === 'list' && (
        <Input
          placeholder={es.strategy.listPlaceholder}
          value={listText}
          onChange={(e) => {
            setListText(e.target.value)
            const vals = e.target.value
              .split(/[,;\s]+/)
              .filter((s) => s.trim() !== '')
              .map(Number)
              .filter((n) => Number.isFinite(n))
            if (vals.length > 0) onChange({ values: vals })
          }}
        />
      )}
      {mode === 'range' && typeof value === 'object' && 'range' in value && (
        <div className="grid grid-cols-3 gap-1">
          {([0, 1, 2] as const).map((i) => (
            <Input
              key={i}
              type="number"
              step="any"
              title={[es.strategy.rangeFrom, es.strategy.rangeTo, es.strategy.rangeStep][i]}
              placeholder={[es.strategy.rangeFrom, es.strategy.rangeTo, es.strategy.rangeStep][i]}
              value={String(value.range[i])}
              onChange={(e) => {
                const r = [...value.range]
                r[i] = Number(e.target.value)
                onChange({ range: r })
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
