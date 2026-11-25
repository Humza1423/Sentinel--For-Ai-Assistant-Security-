import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import IncidentPlayback from './IncidentPlayback'

afterEach(() => { cleanup(); vi.useRealTimers() })
const show = () => render(<IncidentPlayback chatPane={<p>Existing session</p>} onReturn={() => {}} onVerify={() => {}} />)

it('keeps the branch, explanation and chat aligned when seeking backward', () => {
  show()
  const range = screen.getByRole('slider', { name: 'Playback step' })
  fireEvent.change(range, { target: { value: '3' } })
  expect(screen.getByText('Finished checking your transfer.')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: /Record reached model/ }))
  expect(screen.queryByText('Finished checking your transfer.')).toBeNull()
  expect(screen.getByText(/privacy boundary is crossed/)).toBeTruthy()
  expect(range.getAttribute('aria-valuetext')).toBe('Record reached model')
})

it('pauses on demand, completes, and restarts from the beginning', () => {
  vi.useFakeTimers()
  show()
  fireEvent.click(screen.getByRole('button', { name: 'Play example' }))
  act(() => vi.advanceTimersByTime(2200))
  fireEvent.click(screen.getByRole('button', { name: 'Pause playback' }))
  act(() => vi.advanceTimersByTime(9000))
  expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toBe('Lookup allowed')
  fireEvent.click(screen.getByRole('button', { name: 'Play example' }))
  for (let i = 0; i < 2; i++) act(() => vi.advanceTimersByTime(2200))
  expect(screen.getByText('Finished checking your transfer.')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Play example' }))
  expect(screen.getByRole('slider').getAttribute('aria-valuetext')).toBe('Transfer question')
})
