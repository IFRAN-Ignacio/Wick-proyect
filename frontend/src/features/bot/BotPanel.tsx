import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api, unwrap, type Schemas } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { es } from '@/i18n/es'

type Msg = Schemas['BotMessage'] & { tools?: string[]; error?: boolean }

export function BotPanel({ onClose }: { onClose: () => void }) {
  const status = useQuery({
    queryKey: ['bot-status'],
    queryFn: async () => unwrap(await api.GET('/api/v1/bot/status')),
  })
  const [messages, setMessages] = useState<Msg[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  async function send() {
    const q = text.trim()
    if (!q) return
    const history: Msg[] = [...messages, { role: 'user', text: q }]
    setMessages(history)
    setText('')
    setBusy(true)
    try {
      const r = unwrap(
        await api.POST('/api/v1/bot/chat', {
          body: { messages: history.filter((m) => !m.error).map(({ role, text }) => ({ role, text })) },
        }),
      )
      setMessages([...history, { role: 'model', text: r.text, tools: r.tool_calls }])
    } catch (e) {
      setMessages([...history, { role: 'model', text: e instanceof Error ? e.message : String(e), error: true }])
    } finally {
      setBusy(false)
    }
  }

  const available = status.data?.available ?? false
  return (
    <aside className="w-96 shrink-0 border-l border-border flex flex-col h-screen sticky top-0">
      <div className="flex items-center justify-between p-3 border-b border-border">
        <span className="font-semibold">{es.bot.title}</span>
        <Button variant="ghost" size="sm" onClick={onClose}>
          {es.bot.close}
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-3 flex flex-col gap-3 text-sm">
        <div className="text-xs text-muted-foreground">{es.bot.intro}</div>
        {!available && status.data && <div className="text-amber-400">{status.data.message || es.bot.unavailable}</div>}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded p-2 whitespace-pre-wrap ${
              m.role === 'user' ? 'bg-primary/20 self-end' : m.error ? 'bg-rose-500/10 text-rose-300' : 'bg-accent'
            }`}
          >
            {m.text}
            {m.tools && m.tools.length > 0 && (
              <div className="mt-1 text-[10px] text-muted-foreground">
                {es.bot.tools} {m.tools.join(', ')}
              </div>
            )}
          </div>
        ))}
        {busy && <div className="text-muted-foreground">{es.bot.thinking}</div>}
      </div>
      <form
        className="p-3 border-t border-border flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          void send()
        }}
      >
        <Input
          value={text}
          disabled={!available || busy}
          placeholder={es.bot.placeholder}
          onChange={(e) => setText(e.target.value)}
        />
        <Button type="submit" disabled={!available || busy}>
          {es.bot.send}
        </Button>
      </form>
    </aside>
  )
}
