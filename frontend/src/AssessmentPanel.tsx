import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './chatApi'

type Result = {
  case_id?: string
  probe_id?: string
  outcome: string
  run_id: string
  user_message?: string
  response_text?: string | null
  expected?: string
  observed?: string
  event_ids?: string[]
}
type Assessment = {
  assessment_id: string
  status: string
  mode: string
  events: { sequence: number; type: string }[]
  report: { benign: Result[]; controls: Result[] } | null
}

function CheckResult({ result, onInspectRun }: {
  result: Result
  onInspectRun?: (runId: string) => void
}) {
  const label = (result.case_id ?? result.probe_id ?? 'Check').replaceAll(/[-_]/g, ' ')
  return <li>
    <details>
      <summary>{label} — {result.outcome}</summary>
      {result.user_message && <p><b>Question</b> {result.user_message}</p>}
      {result.response_text && <p><b>Assistant response</b> {result.response_text}</p>}
      {result.expected && <p><b>Expected</b> {result.expected}</p>}
      {result.observed && <p><b>Observed</b> {result.observed}</p>}
      {onInspectRun && result.run_id && <button className="export-button"
        onClick={() => onInspectRun(result.run_id)}>Inspect this check</button>}
      {!!result.event_ids?.length && <p>{result.event_ids.length} recorded evidence events</p>}
    </details>
  </li>
}

export default function AssessmentPanel({ sessionId, onInspectRun }: {
  sessionId: string
  onInspectRun?: (runId: string) => void
}) {
  const client = useQueryClient()
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
      client.setQueryData(['assessment', data.assessment_id], data)
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
  const startLabel = start.isError ? 'Retry starting checks' : id ? 'Run new checks' : 'Run banking checks'
  const startChecks = () => {
    // A missing response may follow a successful server start. Retry its same ID.
    const nextRequestId = start.isError && start.variables
      ? start.variables
      : id ? crypto.randomUUID() : requestId
    start.mutate(nextRequestId)
  }
  return <section aria-label="Banking assessment">
    <h3>Check everyday banking behavior</h3>
    <p>Five customer questions use the selected assistant’s tools and synthetic records. Separate permission checks exercise the protected reference. Fixture model · No API cost.</p>
    {(!id || (!active && (data || state.error))) && <button className="export-button"
      disabled={start.isPending} onClick={startChecks}>
      {start.isPending ? 'Starting…' : startLabel}
    </button>}
    {(start.error || state.error || cancel.error) && <p role="alert">{(start.error || state.error || cancel.error)?.message}</p>}
    {state.error && <button className="export-button" disabled={state.isFetching}
      onClick={() => state.refetch()}>Retry loading assessment</button>}
    {data && <p role="status">Assessment {data.status}</p>}
    {active && <button onClick={() => cancel.mutate()} disabled={cancel.isPending}>Cancel assessment</button>}
    {data?.report && <>
      <h4>Customer questions</h4>
      <ul>{data.report.benign.map(result => <CheckResult key={result.case_id} result={result} onInspectRun={onInspectRun} />)}</ul>
      <h4>Reference permission checks</h4>
      <ul>{data.report.controls.map(result => <CheckResult key={result.probe_id} result={result} onInspectRun={onInspectRun} />)}</ul>
      <button className="export-button" onClick={download}>Download report</button>
    </>}
    {!!data?.events.length && <details><summary>Assessment progress</summary>
      <ol>{data.events.map(event => <li key={event.sequence}>{event.type.replaceAll('_', ' ')}</li>)}</ol>
    </details>}
  </section>
}
