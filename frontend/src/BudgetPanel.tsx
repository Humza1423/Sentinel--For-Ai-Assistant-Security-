import { useQuery } from '@tanstack/react-query'
import { api } from './chatApi'

type Budget = {
  currency: string
  initialized: boolean
  recorded_micro_usd: number
  reserved_micro_usd: number
  remaining_micro_usd: number | null
  prior_micro_usd: number | null
  accounting_started_at: string | null
  call_estimate: { estimated_micro_usd: number; maximum_micro_usd: number }
}
const usd = (micro: number) =>
  new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  }).format(micro / 1_000_000)

export default function BudgetPanel() {
  const query = useQuery({
    queryKey: ['usage'],
    queryFn: () => api<Budget>('/api/v2/usage'),
    refetchInterval: 15000,
    retry: false,
  })
  const budget = query.data
  if (!budget || budget.currency !== 'USD')
    return (
      <p className="budget-note">
        {query.error
          ? 'Usage ledger unavailable. Fixture chat remains free.'
          : 'Loading usage ledger…'}
      </p>
    )
  return (
    <details className="budget-panel">
      <summary>
        API budget · Recorded {usd(budget.recorded_micro_usd)} · Reserved{' '}
        {usd(budget.reserved_micro_usd)} ·{' '}
        {budget.initialized
          ? `${usd(budget.remaining_micro_usd ?? 0)} remaining`
          : 'Prior spend not initialized'}
      </summary>
      <p>
        Project ceiling: US$45. Assessment ceiling: US$2. Fixture conversations
        make no provider calls.
      </p>
      {!budget.initialized ? (
        <p>
          Before live use, initialize accounting with any earlier project API
          spend. The available balance is unknown until then.
        </p>
      ) : (
        <p>
          Prior spend: {usd(budget.prior_micro_usd ?? 0)}. Accounting started:{' '}
          {budget.accounting_started_at}.
        </p>
      )}
      <p>
        One-call planning estimate:{' '}
        {usd(budget.call_estimate.estimated_micro_usd)} at 3,000 input / 500
        output tokens. Conservative maximum:{' '}
        {usd(budget.call_estimate.maximum_micro_usd)} at 12,000 input / 2,000
        output. Actual assessment estimates arrive with the campaign workflow.
      </p>
      <p>
        Uncertain charges retain their reservation until usage is confirmed.
        This local ledger covers calls made through Sentinel.
      </p>
    </details>
  )
}
