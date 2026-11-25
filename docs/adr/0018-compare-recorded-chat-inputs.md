# ADR 0018 · Compare actual initial dispatches

Comparing the text typed into chat misses conversation history and context trimming. Reconstructing a prompt later can also introduce different instructions. Compare the independently recorded first dispatch on each side, with evidence references and an explicit unknown result where a receipt is missing. This gives engineers a useful read-only comparison without invoking another model or introducing persistent state.
