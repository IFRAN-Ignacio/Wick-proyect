import { useEffect, useState } from 'react'
import type { Job } from '@/api/client'

/** Sigue un job por SSE (`/api/v1/jobs/{id}/events`) hasta que termina. */
export function useJob(jobId: string | null): Job | null {
  const [job, setJob] = useState<Job | null>(null)
  useEffect(() => {
    if (!jobId) {
      setJob(null)
      return
    }
    const es = new EventSource(`/api/v1/jobs/${jobId}/events`)
    es.onmessage = (ev: MessageEvent<string>) => {
      const snap = JSON.parse(ev.data) as Job
      setJob(snap)
      if (snap.status !== 'running') es.close()
    }
    return () => es.close()
  }, [jobId])
  return job
}
