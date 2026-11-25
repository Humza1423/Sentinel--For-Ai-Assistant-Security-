import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AssessmentPanel from './AssessmentPanel'

afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals() })

it('starts saved fixture checks and displays their separate outcomes', async () => {
  const state = {
    assessment_id: 'saved', status: 'complete', events: [],
    report: { benign: [{ case_id: 'latest-transfer', outcome: 'passed' }],
      controls: [{ probe_id: 'schema_denial', outcome: 'passed' }] },
  }
  const fetch = vi.fn(async (_url: string, _options?: { body?: string }) => ({ ok: true, json: async () => state }))
  vi.stubGlobal('fetch', fetch)
  render(<QueryClientProvider client={new QueryClient()}><AssessmentPanel sessionId="session" /></QueryClientProvider>)
  fireEvent.click(screen.getByText('Run banking checks'))
  expect(await screen.findByText('latest transfer — passed')).toBeTruthy()
  expect(screen.getByText('schema denial — passed')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Run new checks' })).toBeTruthy()
  expect(localStorage.getItem('sentinel-assessment-session')).toBe('saved')
  expect(JSON.parse(fetch.mock.calls[0]?.[1]?.body ?? '{}').session_id).toBe('session')
})

it('lets a saved assessment recover after a loading error', async () => {
  localStorage.setItem('sentinel-assessment-session', 'saved')
  const fetch = vi.fn()
    .mockRejectedValueOnce(new Error('Connection lost'))
    .mockResolvedValue({ ok: true, json: async () => ({ assessment_id: 'saved', status: 'cancelled', events: [], report: null }) })
  vi.stubGlobal('fetch', fetch)
  render(<QueryClientProvider client={new QueryClient()}><AssessmentPanel sessionId="session" /></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Retry loading assessment' }))
  expect(await screen.findByText('Assessment cancelled')).toBeTruthy()
})

it('retries a failed new-start request with the same idempotency ID', async () => {
  localStorage.setItem('sentinel-assessment-session', 'old')
  const requests: string[] = []
  const fetch = vi.fn(async (_url: string, options?: { body?: string }) => {
    if (options?.body) {
      requests.push(JSON.parse(options.body).request_id)
      if (requests.length === 1) throw new Error('Response lost')
    }
    return { ok: true, json: async () => ({ assessment_id: 'old', status: 'complete', events: [], report: null }) }
  })
  vi.stubGlobal('fetch', fetch)
  render(<QueryClientProvider client={new QueryClient()}><AssessmentPanel sessionId="session" /></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Run new checks' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Retry starting checks' }))
  await screen.findByRole('button', { name: 'Run new checks' })
  expect(requests).toHaveLength(2)
  expect(requests[0]).toBe(requests[1])
})

it('opens the existing inspector for a completed case', async () => {
  localStorage.setItem('sentinel-assessment-session', 'saved')
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({
    assessment_id: 'saved', status: 'complete', events: [],
    report: { benign: [{ case_id: 'latest-transfer', outcome: 'passed', run_id: 'run-1', user_message: 'Show latest transfer', response_text: 'Transfer CAD 125', event_ids: ['e-1'] }], controls: [] },
  }) })))
  const inspect = vi.fn()
  render(<QueryClientProvider client={new QueryClient()}><AssessmentPanel sessionId="session" onInspectRun={inspect} /></QueryClientProvider>)
  expect(await screen.findByText('Transfer CAD 125')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Inspect this check' }))
  expect(inspect).toHaveBeenCalledWith('run-1')
})

it.each(['passed', 'inconclusive'] as const)(
  'shows the backend verification result %s and links both runs to evidence',
  async (status) => {
    localStorage.setItem('sentinel-assessment-session', 'saved')
    const baseline = { case_id: 'latest-transfer', run_id: 'baseline', outcome: 'passed', response_text: 'Original CAD 125' }
    const candidate = { ...baseline, run_id: 'candidate', response_text: 'Defended CAD 125' }
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true,
      json: async () => ({
        assessment_id: 'saved', status: 'complete', events: [],
        report: {
          benign: [baseline],
          controls: [],
          baseline_scope: {
            outcome: 'exposed_capability', run_id: 'scope', model_controlled_customer_tools: ['lookup'],
          },
          recommendation: {
            defense_id: 'context_bound_customer_tools_v1',
            likely_cause: 'The gateway takes identity from the model.',
            expected_effect: 'Bind identity to the signed-in session.',
            sources: [],
          },
          verification: {
            status, candidate_benign: [candidate],
            candidate_scope: {
              outcome: 'session_bound', run_id: 'defended-scope', model_controlled_customer_tools: [],
            },
            comparisons: [{
              case_id: 'latest-transfer',
              status: status === 'passed' ? 'matched' : 'inconclusive',
              reason: status === 'inconclusive' ? 'Source identity is unavailable.' : '',
              unexpected_fields: [],
            }],
          },
        },
      }),
    })))
    const inspect = vi.fn()
    render(<QueryClientProvider client={new QueryClient()}>
      <AssessmentPanel sessionId="session" onInspectRun={inspect} />
    </QueryClientProvider>)
    expect(await screen.findByRole('heading', { name: `Verification ${status}` })).toBeTruthy()
    expect(screen.getByText('Original CAD 125')).toBeTruthy()
    expect(screen.getByText('Defended CAD 125')).toBeTruthy()
    if (status === 'inconclusive') {
      expect(screen.getByText('Source identity is unavailable.')).toBeTruthy()
      expect(screen.queryByRole('heading', { name: 'Verification passed' })).toBeNull()
    }
    fireEvent.click(screen.getByRole('button', { name: 'Inspect observed capability' }))
    fireEvent.click(screen.getByRole('button', { name: 'Inspect defended capability' }))
    expect(inspect.mock.calls).toEqual([['scope'], ['defended-scope']])
  },
)
