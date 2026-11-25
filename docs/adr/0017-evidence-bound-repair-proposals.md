# ADR 0017 · Ground repair proposals in one recorded investigation

A rule that maps each violation code to a fix loses information about the cause. Giving a model authority to edit the target at proposal time would collapse review, implementation and verification into a single operation.

Use the recorded investigation as the input to a bounded proposal. The model may suggest a configuration change, reviewed control, source change or combination. Trusted code binds the proposal to the run and revision, limits the change scope and supplies mandatory checks. A separate offline path makes development reproducible. Proposal generation requires no new database table, graph or code execution.
