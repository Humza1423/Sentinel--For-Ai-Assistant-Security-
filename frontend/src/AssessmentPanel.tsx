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
  model_controlled_customer_tools?: string[]
  repository_scope_enforced?: boolean
  source_receipt?: { revision: string | null }
  run_id: string
}

type Verification = {
  status: 'passed' | 'failed' | 'inconclusive'
  candidate_scope: ScopeObservation
  configuration_change: { defense_presets: { before: string[]; after: string[] } }
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

function ScopeCard({ title, scope, onInspectRun, buttonLabel }: {
  title: string
  scope?: ScopeObservation
  onInspectRun?: (runId: string) => void
  buttonLabel: string
}) {
  const descriptions = {
    exposed_capability: 'The model can choose a customer ID.',
    session_bound: 'The signed-in session supplies the customer ID.',
    inconclusive: 'Customer identity could not be established.',
  }
  return <div className="scope-card">
    <h5>{title}</h5>
    <p>{scope ? descriptions[scope.outcome] : 'No capability observation was recorded.'}</p>
    {!!scope?.model_controlled_customer_tools?.length && <p>Tools accepting an ID: <code>{scope.model_controlled_customer_tools.join(', ')}</code></p>}
    {typeof scope?.repository_scope_enforced === 'boolean' &&
      <p>Repository ownership check: {scope.repository_scope_enforced ? 'enforced' : 'absent'}</p>}
    {scope?.run_id && onInspectRun && <button className="export-button"
      onClick={() => onInspectRun(scope.run_id)}>{buttonLabel}</button>}
  </div>
}

function VerificationSummary({ report, onInspectRun }: {
  report: Report
  onInspectRun?: (runId: string) => void
}) {
  const { baseline_scope: observed, recommendation, verification } = report
  if (!observed && !verification) return <p>This saved assessment has no recorded customer-permission comparison.</p>
  return <ol className="verification-steps" aria-label="Security verification">
    <li>
      <h4>Who chooses the customer?</h4>
      <div className="verification-columns">
        <ScopeCard title="Selected assistant" scope={observed} onInspectRun={onInspectRun} buttonLabel="Inspect observed capability" />
        {verification && <ScopeCard title="Defended copy" scope={verification.candidate_scope} onInspectRun={onInspectRun} buttonLabel="Inspect defended capability" />}
      </div>
      {observed?.outcome === 'exposed_capability' &&
        <p>A customer selector is exposed. Establishing a disclosure requires evidence of an actual read or response.</p>}
    </li>
    {recommendation && <>
      <li>
        <h4>Likely cause</h4>
        <p>{recommendation.likely_cause}</p>
        {!!recommendation.sources.length && <details>
          <summary>Source references</summary>
          {observed?.source_receipt?.revision && <p>Revision <code>{observed.source_receipt.revision}</code></p>}
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
      <details>
        <summary>Configuration change</summary>
        <p>Defense presets before: {verification.configuration_change.defense_presets.before.join(', ') || 'None'}</p>
        <p>Defense presets after: {verification.configuration_change.defense_presets.after.join(', ') || 'None'}</p>
      </details>
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
              {baseline ? <ul><CheckResult result={baseline} onInspectRun={onInspectRun} /></ul> : <p>Selected run missing.</p>}
            </div>
            <div><h5>Defended copy</h5>
              {candidate ? <ul><CheckResult result={candidate} onInspectRun={onInspectRun} /></ul> : <p>Defended run missing.</p>}
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
