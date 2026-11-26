# T15B · Verify coverage and receipt ownership on the server

A count alone allows four copies of one permission check to stand in for four distinct checks. The aggregate verdict now requires the named release cases, their successful outcomes on both copies, and each matched pair's two receipt IDs in the correct runs. Known candidate failures still surface as failures. Missing comparison inputs remain inspectable.

The UI displays the stored verdict. Recomputing it in React would give exports and historical reports a second, potentially different interpretation. This change needs no schema migration.
