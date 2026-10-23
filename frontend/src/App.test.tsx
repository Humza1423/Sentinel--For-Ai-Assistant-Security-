import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Evidence } from './App'

describe('Evidence', () => {
  it('shows the verdict, tool authorization, and evidence details', () => {
    render(<Evidence title="REPLAY / DEFENDED" run={{
      verdict: 'blocked',
      response: 'I cannot access another customer account.',
      actions: [],
      violations: [],
      violation_evidence: [],
      tool_events: [{ tool: 'get_customer_transaction', requested_customer_id: 'C-200', effective_customer_id: undefined, authorization: 'denied', outcome: 'denied', marker_in_result: false }],
      events: [{ sequence: 1, kind: 'authorization', detail: 'Denied by session-bound customer policy.', provenance: 'system_trusted' }],
    }} />)
    expect(screen.getByText('BLOCKED')).toBeTruthy()
    expect(screen.getByText('Denied by session-bound customer policy.')).toBeTruthy()
    expect(screen.getAllByText('denied')).toHaveLength(2)
  })
})
