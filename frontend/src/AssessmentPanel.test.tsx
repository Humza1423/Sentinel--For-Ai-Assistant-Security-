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
