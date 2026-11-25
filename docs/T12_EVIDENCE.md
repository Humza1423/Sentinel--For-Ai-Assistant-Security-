# T12 · Comparing recorded chat inputs

Two identical questions can produce different answers. For example, “show my spending” after a discussion of groceries can reach the model with different history than the same question in a fresh chat.

Use GET `/api/v2/runs/{run_id}/input-comparison/{other_run_id}` with the chat owner's cookie. Select two independent chat turns. Each side supplies its own recorded evidence. Ordered message digests represent the actual first model input after history trimming. A prepared live request alone provides insufficient evidence of dispatch.

A difference explains why two runs may be unsuitable for a controlled comparison. Matching fields establish only that those recorded inputs match. Outputs, provider internals and the effectiveness of any repair require separate evidence.
