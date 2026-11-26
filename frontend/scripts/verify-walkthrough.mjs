// Run against the two local services from the README, in a fresh browser session.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const browser = await chromium.launch()
try {
  const page = await browser.newPage({ baseURL: 'http://127.0.0.1:5173', reducedMotion: 'reduce' })
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await page.getByRole('button', { name: 'Watch the example' }).click()
  await page.getByRole('button', { name: /Reply delivered/ }).click()
  await page.getByText('Finished checking your transfer.', { exact: true }).waitFor()
  await page.getByRole('button', { name: 'Open banking chat' }).click()
  await page.getByRole('button', { name: 'Show my latest transfer' }).click()
  await page.getByText(/Peer transfer.*125/).first().waitFor()
  await page.getByRole('button', { name: 'Return to example' }).click()
  await page.getByRole('button', { name: 'Check this assistant' }).click()

  const started = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/v2/assessments' &&
    response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Run privacy checks' }).click()
  const assessment = await (await started).json()
  await page.getByRole('heading', { name: 'The protected copy passed' }).waitFor()

  const saved = await page.request.get('/api/v2/assessments/' + assessment.assessment_id + '/report')
  assert.equal(saved.status(), 200)
  const report = await saved.json()
  for (const [name, scope] of [
    ['See evidence before protection', report.baseline_scope],
    ['See evidence after protection', report.verification.candidate_scope],
  ]) {
    await page.getByRole('button', { name }).click()
    const inspector = page.getByRole('complementary', { name: 'Security inspector' })
    const event = inspector.locator('#event-' + scope.event_id)
    await event.getByText('Evidence details').click()
    await event.getByText(scope.event_id, { exact: true }).waitFor()
    await page.getByRole('button', { name: 'Back to privacy check' }).click()
  }

  const pairLabel = page.getByText('latest transfer · Inputs matched', { exact: true })
  await pairLabel.click()
  const pair = pairLabel.locator('..')
  for (const [side, results] of [
    ['Selected assistant', report.benign],
    ['Defended copy', report.verification.candidate_benign],
  ]) {
    const column = pair.getByRole('heading', { name: side }).locator('..')
    await column.locator('summary').click()
    const answer = results.find(item => item.case_id === 'latest-transfer').response_text
    assert.ok(answer)
    await column.getByText(answer, { exact: false }).last().waitFor()
  }

  const downloading = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download report' }).click()
  const file = await (await downloading).path()
  const exported = JSON.parse(await readFile(file, 'utf8'))
  assert.deepEqual(exported, report)
  assert.equal(exported.mode, 'fixture_execution')
  assert.equal(exported.verification.status, 'passed')
  assert.equal(exported.controls.filter(item => item.outcome === 'passed').length, 4)
  assert.equal(exported.verification.candidate_benign.filter(item => item.outcome === 'passed').length, 5)
  assert.equal(exported.verification.comparisons.filter(item => item.status === 'matched').length, 5)
  assert.deepEqual(errors, [])
  console.log('Walkthrough passed. Both assistants are inspectable and the download matches the saved report.')
} finally {
  await browser.close()
}
