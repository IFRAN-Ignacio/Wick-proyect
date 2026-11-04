import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, unwrap } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { es } from '@/i18n/es'

export function SettingsPage() {
  const status = useQuery({
    queryKey: ['bot-status'],
    queryFn: async () => unwrap(await api.GET('/api/v1/bot/status')),
  })
  const [key, setKey] = useState('')
  const [model, setModel] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  async function act(fn: () => Promise<unknown>) {
    setMsg(null)
    try {
      await fn()
      setMsg(es.settings.saved)
      setKey('')
      void status.refetch()
    } catch (e) {
      setMsg(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="flex flex-col gap-4 max-w-2xl">
      <h1 className="text-2xl font-semibold">{es.settings.title}</h1>
      <Card>
        <CardHeader>
          <CardTitle>{es.settings.apiKey}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-xs text-muted-foreground">{es.settings.apiKeyHelp}</p>
          <div className={status.data?.configured ? 'text-emerald-400 text-sm' : 'text-amber-400 text-sm'}>
            {status.data?.configured ? es.settings.apiKeyConfigured : es.settings.apiKeyMissing}
          </div>
          <div className="flex gap-2">
            <Input type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
            <Button
              disabled={key.trim().length < 10}
              onClick={() => act(async () => unwrap(await api.PUT('/api/v1/settings/api-key', { body: { api_key: key } })))}
            >
              {es.settings.save}
            </Button>
            <Button variant="outline" onClick={() => act(async () => unwrap(await api.DELETE('/api/v1/settings/api-key')))}>
              {es.settings.delete}
            </Button>
          </div>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <Label>{es.settings.model}</Label>
              <Input value={model ?? status.data?.model ?? ''} onChange={(e) => setModel(e.target.value)} />
            </div>
            <Button
              variant="outline"
              disabled={!model}
              onClick={() =>
                act(async () => unwrap(await api.PUT('/api/v1/settings/bot-model', { params: { query: { model: model! } } })))
              }
            >
              {es.settings.saveModel}
            </Button>
          </div>
          {msg && <div className="text-sm">{msg}</div>}
        </CardContent>
      </Card>
      <p className="text-xs text-muted-foreground">{es.settings.privacy}</p>
    </div>
  )
}
