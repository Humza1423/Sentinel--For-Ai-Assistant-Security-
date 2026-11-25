import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from './chatApi'

type Result = { case_id?: string; probe_id?: string; outcome: string; run_id: string }
type Assessment = {
  assessment_id: string
  status: string
  mode: string
  events: { sequence: number; type: string }[]
  report: { benign: Result[]; controls: Result[] } | null
}

export default function AssessmentPanel({ sessionId }: { sessionId: string }) {
  const [id, setId] = useState<string | null>(() => localStorage.getItem(`sentinel-assessment-${sessionId}`))
  const [requestId] = useState(() => crypto.randomUUID())
  const state = useQuery({
    queryKey: ['assessment', id],
    queryFn: () => api<Assessment>(`/api/v2/assessments/${id}`),
    enabled: !!id,
    refetchInterval: (query) => ['queued', 'running'].includes(query.state.data?.status ?? '') ? 750 : false,
    retry: false,
  })
  const start = useMutation({
    mutationFn: (nextRequestId: string) => api<Assessment>('/api/v2/assessments', {
      method: 'POST', body: JSON.stringify({ session_id: sessionId, request_id: nextRequestId }),
    }),
    onSuccess: (data) => {
      localStorage.setItem(`sentinel-assessment-${sessionId}`, data.assessment_id)
      setId(data.assessment_id)
    },
  })
  const cancel = useMutation({
    mutationFn: () => api(`/api/v2/assessments/${id}/cancel`, { method: 'POST' }),
    onSuccess: () => state.refetch(),
  })
  const data = state.data
  const active = ['queued', 'running'].includes(data?.status ?? '')
  const download = () => {
    const blob = new Blob([JSON.stringify(data?.report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'sentinel-banking-evaluation.json'
    link.click()
    URL.revokeObjectURL(url)
  }
  return <section aria-label="Banking assessment">
    <h3>Check everyday banking behavior</h3>
    <p>Five customer questions use the selected assistant’s tools and synthetic records. Separate permission checks exercise the protected reference. Fixture model · No API cost.</p>
    {!id && <button className="export-button" disabled={start.isPending} onClick={() => start.mutate(requestId)}>
      {start.isPending ? 'Starting…' : 'Run banking checks'}
    </button>}
    {(start.error || state.error || cancel.error) && <p role="alert">{(start.error || state.error || cancel.error)?.message}</p>}
    {!!id && !active && (data || state.error) && <button className="export-button"
      disabled={start.isPending} onClick={() => start.mutate(crypto.randomUUID())}>
      Run new checks
    </button>}
    {data && <p role="status">Assessment {data.status}</p>}
    {active && <button onClick={() => cancel.mutate()} disabled={cancel.isPending}>Cancel assessment</button>}
    {data?.report && <>
      <h4>Customer questions</h4>
      <ul>{data.report.benign.map(r => <li key={r.case_id}>{r.case_id?.replaceAll('-', ' ')} — {r.outcome}</li>)}</ul>
      <h4>Reference permission checks</h4>
      <ul>{data.report.controls.map(r => <li key={r.probe_id}>{r.probe_id?.replaceAll('_', ' ')} — {r.outcome}</li>)}</ul>
      <button className="export-button" onClick={download}>Download report</button>
    </>}
    {!!data?.events.length && <details><summary>Assessment progress</summary>
      <ol>{data.events.map(e => <li key={e.sequence}>{e.type.replaceAll('_', ' ')}</li>)}</ol>
    </details>}
  </section>
}
