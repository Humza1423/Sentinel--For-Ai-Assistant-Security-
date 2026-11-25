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
