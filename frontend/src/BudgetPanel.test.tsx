import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BudgetPanel from './BudgetPanel'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('shows an unknown balance until previous spend is initialized', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => ({
      ok: true,
      json: async () => ({
        currency: 'USD',
        initialized: false,
        recorded_micro_usd: 0,
        reserved_micro_usd: 0,
        remaining_micro_usd: null,
        call_estimate: { estimated_micro_usd: 550, maximum_micro_usd: 4000 },
      }),
    })),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <BudgetPanel />
    </QueryClientProvider>,
  )
  expect(await screen.findByText(/Prior spend not initialized/)).toBeTruthy()
  expect(screen.getByText(/available balance is unknown/)).toBeTruthy()
})
