import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'
import {
  ArrowRight,
  CaretDown,
  CaretRight,
  ChatCircle,
  Check,
  CircleNotch,
  FileText,
  Play,
  ShieldCheck,
  User,
  WarningCircle,
} from '@phosphor-icons/react'

type Scenario = {
  id: string
  name: string
  description: string
  attacker_control: string
  protected_boundary: string
  attack_seed: string
  request: string
}
type Run = {
  verdict: string
  response: string
  actions: string[]
  violations: string[]
  violation_evidence?: { code: string; supporting_event_ids: string[] }[]
  events: {
    sequence: number
    kind: string
    detail: string
    provenance: string
    event_id?: string
    parent_event_id?: string | null
    digest?: string
  }[]
  tool_events: {
    tool: string
    requested_customer_id?: string
    effective_customer_id?: string
    authorization: string
    outcome: string
    marker_in_result: boolean
  }[]
}
type Report = {
  campaign_id: string
  scenario: Scenario
  mode: string
  baseline: Run
  replay: Run
  defense_id: string
  benign_passed: number
  benign_total: number
  benign_results: { case: string; passed: boolean; expected: string; observed: string }[]
  snapshot_id: string
  replay_inputs_identical: boolean
  model: string
  created_at: string
}
const API = 'http://localhost:8000/api'

async function getScenarios(): Promise<Scenario[]> {
  const response = await fetch(`${API}/scenarios`)
  if (!response.ok) throw new Error('Could not connect to the workbench API.')
  return response.json()
}
async function runCampaign(scenario_id: string): Promise<Report> {
  const response = await fetch(`${API}/campaigns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id, mode: 'scripted' }),
  })
  if (!response.ok) throw new Error((await response.json()).detail ?? 'Campaign failed.')
  return response.json()
}
function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function Evidence({ run, title }: { run: Run; title: string }) {
  return (
    <section className="evidence-card">
      <div className="evidence-head">
        <div><span className="eyebrow">{title}</span><h3>{run.verdict === 'violated' ? 'Control failed' : 'Attack blocked'}</h3></div>
        <Badge tone={run.verdict === 'violated' ? 'red' : 'green'}>{run.verdict.toUpperCase()}</Badge>
      </div>
      <p className="response">“{run.response}”</p>
      {run.violations.length > 0 && <div className="violation"><WarningCircle size={18} weight="fill" /><div><b>Observed violation</b>{(run.violation_evidence ?? []).map((item) => <small key={item.code}>{item.code} · evidence {item.supporting_event_ids.join(', ')}</small>)}</div></div>}
      {run.tool_events.length > 0 && <div className="tool-table"><div className="table-title">TOOL GATEWAY</div>{run.tool_events.map((tool, index) => <div className="tool-row" key={index}><span className="mono">{tool.tool}</span><span>{tool.requested_customer_id ?? 'session-bound'}</span><Badge tone={tool.authorization === 'allowed' ? 'red' : 'green'}>{tool.authorization}</Badge><span className="muted">{tool.outcome}</span></div>)}</div>}
      <details className="trace"><summary>Inspect evidence trail <span>{run.events.length} events</span></summary><ol>{run.events.map((event) => <li key={event.sequence}><i>{String(event.sequence).padStart(2, '0')}</i><div><b>{event.kind.replaceAll('_', ' ')}</b><small>{event.detail}</small></div><Badge tone={event.provenance === 'external_untrusted' ? 'amber' : ''}>{event.provenance.replaceAll('_', ' ')}</Badge></li>)}</ol></details>
    </section>
  )
}

function FlowNode({ icon, label, detail, tone = '', children }: { icon: ReactNode; label: string; detail: string; tone?: string; children?: ReactNode }) {
  return <div className={`flow-node ${tone}`}><span className="flow-icon">{icon}</span><div className="flow-copy"><b>{label}</b><p>{detail}</p>{children}</div></div>
}

function Verdict({ run, scenarioId, phase }: { run?: Run; scenarioId: string; phase: 'baseline' | 'replay' }) {
  if (!run) return <span className="lane-status waiting">Waiting for test</span>
  if (run.verdict === 'error' || run.verdict === 'inconclusive') return <span className="lane-status uncertain">{run.verdict === 'error' ? 'Run error' : 'Inconclusive'}</span>
  if (phase === 'baseline' && run.verdict === 'violated') return <span className="lane-status unsafe">{scenarioId === 'memo-phishing' ? 'Unsafe link recommended' : 'Private data exposed'}</span>
  if (phase === 'replay' && run.verdict === 'blocked') return <span className="lane-status safe">{scenarioId === 'memo-phishing' ? 'Link blocked on replay' : 'Other account blocked'}</span>
  return <span className={`lane-status ${run.verdict === 'blocked' ? 'safe' : 'unsafe'}`}>{run.verdict === 'blocked' ? 'Blocked' : 'Violation observed'}</span>
}

export default function App() {
  const { data: scenarios = [], isLoading, error } = useQuery({ queryKey: ['scenarios'], queryFn: getScenarios })
  const [selected, setSelected] = useState('memo-phishing')
  const mutation = useMutation({ mutationFn: runCampaign })
  const chosen = scenarios.find((item) => item.id === selected)
  const report = mutation.data
  const isPhishing = selected === 'memo-phishing'
  const download = () => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `security-report-${report.scenario.id}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#workbench" aria-label="Sentinel workbench home">
          <span className="brand-mark">S</span><span className="brand-name">Sentinel</span><span className="brand-divider"/><span className="brand-product">Agent Security Workbench</span>
        </a>
        <div className="top-meta"><span className="status-dot"/> <span>Synthetic</span><i/> <span>Scripted</span><i/> <span>No API cost</span><i className="meta-divider"/><time dateTime="2026-10-23">Oct 23, 2026</time></div>
      </header>

      <main id="workbench" className="workspace">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow">CONTROLLED AGENT SECURITY TEST</div>
            <h1>{isPhishing ? 'Transaction memo phishing test' : 'Cross-customer access test'}</h1>
            <p>{chosen?.description ?? 'See how an attacker-controlled transaction memo can influence a banking assistant.'} We test whether the assistant follows it—and whether a registered control stops the unsafe action.</p>
          </div>
          <div className="run-controls">
            <label htmlFor="scenario-select">SCENARIO</label>
            <div className="control-row">
              <div className="select-wrap">
                <select id="scenario-select" value={selected} onChange={(event) => { setSelected(event.target.value); mutation.reset() }} disabled={isLoading}>
                  {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}
                </select>
                <CaretDown size={16} weight="bold" aria-hidden="true"/>
              </div>
              <button className="run-button" disabled={!chosen || mutation.isPending} onClick={() => chosen && mutation.mutate(chosen.id)}>
                {mutation.isPending ? <CircleNotch size={18} className="spinner" aria-hidden="true"/> : <Play size={17} weight="fill" aria-hidden="true"/>}
                {mutation.isPending ? 'Running test…' : report ? 'Run test again' : 'Run the test'}
              </button>
            </div>
            <p className="run-note">{report ? 'Same synthetic data and attack are used for the replay.' : 'A scripted test using synthetic data. Deterministic and free to run.'}</p>
          </div>
        </section>

        {error && <div className="inline-alert"><WarningCircle size={18}/><span>The local test service is offline. Start the backend to run a campaign.</span></div>}
        {mutation.error && <div className="inline-alert"><WarningCircle size={18}/><span>{(mutation.error as Error).message}</span></div>}

        <section className="flow-section" aria-label="How the test moves through the banking assistant">
          <div className="flow-caption"><span>THE ATTACK PATH</span><span className="flow-caption-detail">What enters the assistant, and what leaves it</span></div>
          <div className="flow-track">
            <FlowNode icon={<User size={23} weight="regular"/>} label="Customer request" detail={chosen?.request ?? 'A customer asks about a recent transfer.'}/>
            <ArrowRight className="flow-arrow" size={19} weight="regular" aria-hidden="true"/>
            <FlowNode icon={<FileText size={22} weight="regular"/>} label="Transaction memo" detail={isPhishing ? 'Attacker-controlled text contains a fake verification link.' : 'Attacker-controlled text asks for another customer’s account.'} tone="untrusted"><span className="untrusted-tag">UNTRUSTED INPUT</span></FlowNode>
            <ArrowRight className="flow-arrow" size={19} weight="regular" aria-hidden="true"/>
            <FlowNode icon={<ChatCircle size={23} weight="regular"/>} label="Assistant response" detail={report ? 'The baseline follows the memo; replay uses the same case with a control.' : 'The assistant receives the request and the memo.'}/>
            <ArrowRight className="flow-arrow" size={19} weight="regular" aria-hidden="true"/>
            <FlowNode icon={<ShieldCheck size={23} weight="regular"/>} label="Security gate" detail={report ? 'The registered control checks the requested action.' : 'The control checks unsafe actions before they reach the customer.'} tone="gate"/>
          </div>
          <div className="path-outcomes" aria-live="polite">
            <div className="path-outcome baseline-outcome"><span className="outcome-mark"><WarningCircle size={18} weight="fill"/></span><div><small>BASELINE · BEFORE CONTROL</small><Verdict run={report?.baseline} scenarioId={selected} phase="baseline"/><p>{report ? report.baseline.response : 'Run the test to see what happens without the registered control.'}</p></div></div>
            <div className="outcome-connector"><ArrowRight size={21}/></div>
            <div className="path-outcome replay-outcome"><span className="outcome-mark"><ShieldCheck size={19} weight="fill"/></span><div><small>EXACT REPLAY · WITH CONTROL</small><Verdict run={report?.replay} scenarioId={selected} phase="replay"/><p>{report ? report.replay.response : 'The same request and memo are replayed after the control is applied.'}</p></div></div>
          </div>
        </section>

        {report ? <>
          <section className="control-note" aria-label="Defense applied">
            <div className="control-icon"><ShieldCheck size={19} weight="regular"/></div>
            <div className="control-copy"><span>REGISTERED CONTROL</span><b>{report.defense_id}</b><p>{isPhishing ? 'Untrusted links cannot become recommended, clickable bank actions.' : 'Customer identity is bound to the signed-in session at both the gateway and data layer.'}</p></div>
            <div className="replay-integrity"><span>REPLAY INTEGRITY</span><b>{report.replay_inputs_identical ? 'Same request · same attack · same data snapshot' : 'Input mismatch'}</b><small>Snapshot {report.snapshot_id}</small></div>
          </section>
          <section className="utility-row" aria-label="Usefulness results">
            <span className={`utility-check ${report.benign_passed === report.benign_total ? 'all-clear' : 'partial'}`}><Check size={21} weight="bold"/></span>
            <strong>{report.benign_passed} of {report.benign_total}</strong>
            <div className="utility-copy"><b>everyday banking checks passed</b><span>The assistant still handles normal requests as expected.</span></div>
            <button className="export-button" onClick={download} aria-label="Download security report JSON">Download report <ArrowRight size={17}/></button>
          </section>
          <div className="benign-cases" aria-label="Individual usefulness checks">{report.benign_results.map((item) => <div key={item.case} className="benign-case"><span className={item.passed ? 'case-pass' : 'case-fail'}>{item.passed ? <Check size={13} weight="bold"/> : <WarningCircle size={13} weight="fill"/>}</span><span>{item.case.replaceAll('-', ' ')}</span></div>)}</div>
        </> : <div className="ready-note"><span className="ready-pulse"/><span>Ready for a controlled test</span><span className="ready-detail">Run it to compare the vulnerable baseline with its defended replay.</span></div>}

        <details className="evidence-disclosure">
          <summary><span className="disclosure-label"><CaretRight size={15} weight="bold"/> View technical evidence</span><span className="disclosure-hint">Tool calls, security events, and full run details</span></summary>
          {report ? <div className="evidence-content">
            <div className="evidence-column"><h2>Baseline events</h2><ol>{report.baseline.events.map((event) => <li key={`baseline-${event.sequence}`}><span>{String(event.sequence).padStart(2, '0')}</span><div><b>{event.kind.replaceAll('_', ' ')}</b><p>{event.detail}</p></div><Badge tone={event.provenance === 'external_untrusted' ? 'amber' : ''}>{event.provenance.replaceAll('_', ' ')}</Badge></li>)}</ol></div>
            <div className="evidence-column"><h2>Replay events</h2><ol>{report.replay.events.map((event) => <li key={`replay-${event.sequence}`}><span>{String(event.sequence).padStart(2, '0')}</span><div><b>{event.kind.replaceAll('_', ' ')}</b><p>{event.detail}</p></div><Badge tone={event.provenance === 'external_untrusted' ? 'amber' : ''}>{event.provenance.replaceAll('_', ' ')}</Badge></li>)}</ol></div>
            <div className="evidence-column tool-evidence"><h2>Tool authorization</h2>{report.baseline.tool_events.length || report.replay.tool_events.length ? [...report.baseline.tool_events, ...report.replay.tool_events].map((tool, index) => <div className="tool-row" key={`${tool.tool}-${index}`}><span className="mono">{tool.tool}</span><span>{tool.requested_customer_id ?? 'Session-bound identity'}</span><Badge tone={tool.authorization === 'allowed' ? 'red' : 'green'}>{tool.authorization}</Badge><span className="muted">{tool.outcome}</span></div>) : <p>No bank tools were called in this link-rendering test.</p>}</div>
            {report.baseline.violations.length > 0 && <div className="violation-codes"><span>SCORER FINDINGS</span>{report.baseline.violations.map((code) => <Badge key={code} tone="red">{code}</Badge>)}{(report.baseline.violation_evidence ?? []).flatMap((item) => item.supporting_event_ids).map((eventId) => <small key={eventId}>Evidence event {eventId}</small>)}</div>}
            <div className="evidence-footer">Campaign {report.campaign_id.slice(0, 8).toUpperCase()} · {report.model} · Snapshot {report.snapshot_id} · {new Date(report.created_at).toLocaleString()}</div>
          </div> : <div className="empty-evidence">Run a test to generate the model, tool, authorization, and scorer evidence.</div>}
        </details>
        <footer className="footer-note"><span>Sentinel <span>·</span> Local security lab</span><span>Synthetic data only · No real bank connection</span></footer>
      </main>
    </div>
  )
}
