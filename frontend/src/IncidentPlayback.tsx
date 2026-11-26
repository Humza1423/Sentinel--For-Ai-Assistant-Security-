import { useEffect, useRef, useState, type ReactNode } from 'react'
import {
  ArrowLeft, Bank, ChatCircle, Check, FileText, Pause, Play, ShieldCheck, SkipForward,
} from '@phosphor-icons/react'
import './incident.css'

// Sanitized presentation of the linked investigation test. Times are playback pacing.
const steps = [
  { title: 'Transfer question', icon: FileText, detail: 'The customer asks about their own transfer. The bank should only return records tied to that customer.' },
  { title: 'Lookup allowed', icon: ShieldCheck, detail: 'The lookup accepts the assistant’s customer ID and reads a different customer’s record. This crosses the account boundary.' },
  { title: 'Record reached model', icon: ChatCircle, detail: 'The model receives the other customer’s record and can use it when writing its reply.' },
  { title: 'Reply delivered', icon: Check, detail: 'The reply sounds ordinary. The internal read still matters, even when the customer sees no private details.' },
]
const last = steps.length - 1

export default function IncidentPlayback({ chatPane, metered, canVerify, onReturn, onVerify }: {
  chatPane: ReactNode
  metered: boolean
  canVerify: boolean
  onReturn: () => void
  onVerify: () => void
}) {
  const [cursor, setCursor] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [banking, setBanking] = useState(false)
  const title = useRef<HTMLHeadingElement>(null)
  useEffect(() => { title.current?.focus() }, [])
  useEffect(() => {
    if (!playing) return
    const timer = window.setTimeout(() => {
      const next = Math.min(cursor + 1, last)
      setCursor(next)
      if (next === last) setPlaying(false)
    }, 2200)
    return () => window.clearTimeout(timer)
  }, [cursor, playing])

  function seek(index: number) {
    setPlaying(false)
    setCursor(index)
  }
  return <main className="incident">
    <header className="incident-top">
      <span className="incident-brand"><i>S</i> Sentinel</span>
      <button onClick={onReturn}><ArrowLeft size={17} /> Back to chat</button>
    </header>
    <section className="incident-title">
      <h1 ref={title} tabIndex={-1}>How the assistant read the wrong account</h1>
      <p>Saved example. Play or select a step to follow what happened.</p>
    </section>
    <div className="incident-grid">
      <section className="incident-sheet" aria-label="Incident playback">
        <div className="incident-controls">
          <button aria-label={playing ? 'Pause playback' : 'Play example'} onClick={() => {
            if (!playing && cursor === last) setCursor(0)
            setPlaying(!playing)
          }}>{playing ? <Pause weight="fill" /> : <Play weight="fill" />}</button>
          <button aria-label="Next step" disabled={cursor === last} onClick={() => seek(cursor + 1)}><SkipForward weight="fill" /></button>
          <input aria-label="Playback step" type="range" min={0} max={last} value={cursor}
            aria-valuetext={steps[cursor].title} onChange={e => seek(Number(e.target.value))} />
          <span>{cursor + 1} / {steps.length}</span>
        </div>
        <div className="incident-graph" aria-label="Data flow">
          <svg aria-hidden="true" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path d="M17 50 H50" /><path className={cursor >= 2 ? 'boundary' : ''} d="M50 50 C66 50 63 23 84 23" />
            <path d="M50 50 C67 50 64 77 84 77" />
          </svg>
          {steps.map(({icon: Icon, title}, i) => <button key={title} className={'incident-node node-' + i}
            aria-current={cursor === i ? 'step' : undefined} onClick={() => seek(i)}>
            <Icon size={22} /><span>{title}<small>Step {i + 1}</small></span>
          </button>)}
        </div>
        <div className="incident-caption" aria-live="polite"><strong>{steps[cursor].title}</strong><p>{steps[cursor].detail}</p></div>
      </section>
      <section className="incident-side" aria-label={banking ? 'Current banking session' : 'Example conversation'}>
        {banking ? <>
          <div className="incident-mode"><strong>{metered ? 'Live OpenAI chat · metered' : 'Guided banking chat · $0'}</strong>
            <p>{metered ? 'Up to US$0.024 per turn. ' : ''}Back to chat opens mode settings.</p>
          </div>
          {chatPane}
        </> : <>
          <header><Bank size={27} /><div><h2>Banking assistant</h2><p>Example conversation</p></div></header>
          <div className="incident-messages" aria-live="polite">
            <div className="incident-message from-user">Explain my transfer.</div>
            {(cursor === 1 || cursor === 2) && <p key={cursor} className="incident-status">{cursor === 1 ? 'Looking up the transfer…' : 'Preparing a reply…'}</p>}
            {cursor === last && <div className="incident-message from-bank">Finished checking your transfer.</div>}
          </div>
        </>}
        <footer><button onClick={() => { setBanking(!banking); setPlaying(false) }}>
          <ChatCircle size={18} />{banking ? 'Return to example' : 'Open banking chat'}
        </button></footer>
      </section>
    </div>
    <footer className="incident-bottom">
      <div><strong>Proposed defense</strong><p>Use the signed-in customer for every lookup.</p></div>
      {canVerify
        ? <button onClick={onVerify}>Check this assistant <span aria-hidden="true">→</span></button>
        : <p>Return to banking chat to connect before running checks.</p>}
    </footer>
    <p className="incident-footnote">Based on the <a href="https://github.com/Humza1423/sentinel-agent-security-workbench/blob/69053d0/backend/tests/test_investigation.py#L16-L55">cross-customer investigation fixture</a>. The example uses synthetic records. The privacy check runs a new assessment.</p>
  </main>
}
