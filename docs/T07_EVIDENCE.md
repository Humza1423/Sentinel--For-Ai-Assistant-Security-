# T07 — banking chat beside its evidence

`ChatWorkspace.tsx` sends questions through T06's session API and selects the
returned run's persisted events. The inspector exposes authorization, bank reads,
model-context dispatch and output, without inventing security verdicts.
`chatApi.ts` defines typed HTTP inputs/outputs. TanStack Query tracks loading,
failures and event pagination. The existing design tokens and responsive columns
preserve the selected visual direction.

Browser verification ran a real synthetic spending query and inspected its events.
Tests cover chat/evidence wiring, errors, target handoff, old-session completion
and lost-response retries. Offline language support remains explicitly limited;
T09 supplies live conversation.

Interview explanation: “Each answer connects to its actual execution trail, so an
engineer can inspect permissions and data access directly from the conversation.”
