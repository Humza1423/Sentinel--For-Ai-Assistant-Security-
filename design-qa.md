# Design QA — Sentinel workbench

final result: passed

## Comparison target

- Source visual truth: the selected finance-style concept (1487 × 1058 px), reviewed locally. The original generated reference is not distributed with this repository.
- Implementation: `http://127.0.0.1:5173/` in the Codex in-app browser. The CUA browser capture was emitted inline for review; its API did not provide a persistent local screenshot path.
- Implementation capture: 1024 × 720 px. The browser tool did not expose CSS viewport size or device scale factor. The source and capture ratios are close (1.405 and 1.422); comparison was proportional, with no pixel-density conversion available.
- State: transaction memo phishing scenario, completed scripted campaign, evidence disclosure collapsed. The cross-customer disclosure scenario and expanded evidence state were separately tested.

## Visual review

- Full view: the selected source's pale finance aesthetic, title-and-run area, attack path, baseline/replay story, usefulness proof, and secondary evidence disclosure are represented. At the narrower in-app viewport the path and comparison adapt vertically; at the source's wider desktop width they retain the horizontal arrangement.
- Focused regions: inspected the header and run controls, attack path, baseline/replay results, defense and usefulness summary, and expanded technical evidence. No separate detail crop was needed at the capture scale.
- Typography: Manrope for product UI and DM Mono for compact metadata; hierarchy, weight, and spacing remain consistent with the source. Body text stays readable and wraps rather than forcing long attack text into fixed columns.
- Spacing and layout: generous page margins, separated regions, minimal borders, and responsive flow. The first narrow-window capture exposed horizontal clipping; after the responsive changes, the final capture has no horizontal scrollbar and the lower footer wraps cleanly.
- Color and tokens: pearl-white base, dark navy text, blue information cues, coral untrusted/baseline cues, and mint defended/success cues match the visual target.
- Assets and icons: background wash is a generated raster asset at `frontend/src/assets/pearl-flow-background.jpg` (optimized from 1.3 MB PNG to 71 KB JPEG). UI symbols use Phosphor icons; no hand-drawn CSS/SVG icons were substituted.
- Copy: uses the actual synthetic scenario and campaign results. The fake URL is displayed as untrusted text, and the scripted/no-cost status is explicit. No real bank or live-model behavior is implied.

## Findings

No actionable P0, P1, or P2 visual issues remain.

## Comparison history

1. First implementation capture: right-side content clipped in the in-app window; the event path remained too wide and the run/header controls crowded the edge. Severity: P2.
2. Fix: added a stacked flow for narrower viewports, simplified narrow-window metadata, wrapped the report action/footer, and constrained horizontal overflow.
3. Post-fix capture: the path is readable vertically, the result comparison and utility checks fit, and the footer is visible without a horizontal scrollbar. No remaining P0/P1/P2 issue observed.

## Test evidence and limitations

- Frontend: `npm test` — 1 test passed.
- Frontend production build: `npm run build` — passed.
- Backend: `.venv/bin/python -m pytest -q` — 15 tests passed.
- Browser: ran the phishing and cross-customer scripted campaigns; verified the attack verdict, replay verdict, 5/5 usefulness results, and evidence disclosure.
- The CUA browser surface does not expose a console-log inspection API in this workflow; no runtime error appeared in the rendered UI, and all tested interactions completed.

## Follow-up polish (P3)

- On a narrow-height window, the deliberately vertical event path places some results below the fold. This is an intentional responsive tradeoff; a future pass could offer a compact/expanded path toggle.
- Capture a same-size 1440 × 1024 browser screenshot when a larger preview viewport is available for pixel-level typography and spacing comparison.
