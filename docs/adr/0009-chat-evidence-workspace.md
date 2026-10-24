# ADR 0009 — Chat and observed-run inspector

Use existing React/TanStack Query and visual tokens. Each assistant answer selects
its actual run ID; the inspector loads persisted, paginated events. Avoid a second
demo-only chat or another UI framework. The previous campaign remains explicitly
scripted. “Assess assistant” shows the selected manifest with an availability
notice until the assessment graph exists.

Vite development/preview proxy /api to the backend, preserving same-origin session
cookies. Hosted deployment will require the equivalent reverse proxy. Retry IDs
remain stable; old-session responses cannot update a new session; refetch blocks
conflicting writes. Technical payloads expand on demand and prose stays inert.
