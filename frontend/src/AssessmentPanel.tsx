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
type ScopeObservation = {
  outcome: 'exposed_capability' | 'session_bound' | 'inconclusive'
  model_controlled_customer_tools: string[]
  run_id: string
}

type Verification = {
  status: 'passed' | 'failed' | 'inconclusive'
  candidate_scope: ScopeObservation
  candidate_benign: Result[]
  comparisons: {
    case_id: string
    status: 'matched' | 'mismatched' | 'inconclusive'
    unexpected_fields: string[]
    reason: string
  }[]
}

type Report = {
  benign: Result[]
  controls: Result[]
  baseline_scope?: ScopeObservation
  recommendation?: {
    defense_id: string
    expected_effect: string
    likely_cause: string
    sources: { path: string; start: number; end: number }[]
  } | null
  verification?: Verification
}

type Assessment = {
  assessment_id: string
  status: string
  mode: string
  events: { sequence: number; type: string }[]
  report: Report | null
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

function VerificationSummary({ report, onInspectRun }: {
  report: Report
  onInspectRun?: (runId: string) => void
}) {
  const { baseline_scope: observed, recommendation, verification } = report
  if (!observed) return null

  const conclusion = {
    exposed_capability: 'The selected assistant lets the model supply a customer ID.',
    session_bound: 'The selected assistant binds customer identity to the session.',
    inconclusive: 'The recorded tool settings were insufficient to establish customer scope.',
  }[observed.outcome]

  return <ol className="verification-steps" aria-label="Security verification">
    <li>
      <h4>Observed capability</h4>
      <p>{conclusion}</p>
      {observed.outcome === 'exposed_capability' &&
        <p>This check establishes tool authority. It does not test whether the model disclosed a record.</p>}
      {onInspectRun && <button className="export-button" onClick={() => onInspectRun(observed.run_id)}>
        Inspect observed capability
      </button>}
    </li>
    {recommendation && <>
      <li>
        <h4>Likely cause</h4>
        <p>{recommendation.likely_cause}</p>
        {!!recommendation.sources.length && <details>
          <summary>Source references</summary>
          <ul>{recommendation.sources.map(source => <li key={source.path}>
            <code>{source.path}:{source.start}–{source.end}</code>
          </li>)}</ul>
        </details>}
      </li>
      <li>
        <h4>Recommended defense</h4>
        <p>{recommendation.expected_effect}</p>
        <code>{recommendation.defense_id}</code>
      </li>
    </>}
    {verification && <li>
      <h4>Verification {verification.status}</h4>
      <p>The registered defense was applied to a separate copy. The selected chat keeps its original settings.</p>
      <p>
        {report.controls.filter(check => check.outcome === 'passed').length} of {report.controls.length} permission checks passed ·{' '}
        {verification.candidate_benign.filter(check => check.outcome === 'passed').length} of {verification.candidate_benign.length} banking checks passed ·{' '}
        {verification.comparisons.filter(pair => pair.status === 'matched').length} of {verification.comparisons.length} inputs matched
      </p>
      {onInspectRun && <button className="export-button" onClick={() => onInspectRun(verification.candidate_scope.run_id)}>
        Inspect defended capability
      </button>}
    </li>}
  </ol>
}

function BankingComparison({ report, onInspectRun }: {
  report: Report & { verification: Verification }
  onInspectRun?: (runId: string) => void
}) {
  return <>
    <h4>Banking questions before and after</h4>
    <div className="verification-pairs">
      {report.verification.comparisons.map(pair => {
        const baseline = report.benign.find(result => result.case_id === pair.case_id)
        const candidate = report.verification.candidate_benign.find(result => result.case_id === pair.case_id)
        return <details key={pair.case_id}>
          <summary>{pair.case_id.replaceAll('-', ' ')} · Inputs {pair.status}</summary>
          {pair.reason && <p>{pair.reason}</p>}
          {!!pair.unexpected_fields.length && <p>Input differences: {pair.unexpected_fields.join(', ')}</p>}
          <div className="verification-columns">
            <div><h5>Selected assistant</h5>
              <ul>{baseline && <CheckResult result={baseline} onInspectRun={onInspectRun} />}</ul>
            </div>
            <div><h5>Defended copy</h5>
              <ul>{candidate && <CheckResult result={candidate} onInspectRun={onInspectRun} />}</ul>
            </div>
          </div>
        </details>
      })}
    </div>
  </>
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
    <h3>Verify customer permissions</h3>
    <p>Inspect the selected assistant and verify a registered defense when needed. Fixture model · Synthetic records · No API cost.</p>
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
      <VerificationSummary report={data.report} onInspectRun={onInspectRun} />
      {data.report.verification
        ? <BankingComparison report={{ ...data.report, verification: data.report.verification }} onInspectRun={onInspectRun} />
        : <>
          <h4>Customer questions</h4>
          <ul>{data.report.benign.map(result => <CheckResult key={result.case_id} result={result} onInspectRun={onInspectRun} />)}</ul>
        </>}
      <h4>{data.report.verification ? 'Defended copy permission checks' : 'Reference permission checks'}</h4>
      <ul>{data.report.controls.map(result => <CheckResult key={result.probe_id} result={result} onInspectRun={onInspectRun} />)}</ul>
      <button className="export-button" onClick={download}>Download report</button>
    </>}
    {!!data?.events.length && <details><summary>Assessment progress</summary>
      <ol>{data.events.map(event => <li key={event.sequence}>{event.type.replaceAll('_', ' ')}</li>)}</ol>
    </details>}
  </section>
}
