# Student 4 — post-update IR retest results (fill from NEW evidence only)

**System version/commit:** ______________  **Date/time:** ______________
**Python environment and embedding cache:** ______________
**Baseline:** `audit/evidence/baseline/environment.json`
**Working database integrity verified:** Yes / No / Inconclusive

**Assessment rule:** Record **PASS / FAIL / INCONCLUSIVE** based on each case's expected criteria *and actual observed output*. A runner exit code of 0 only proves collection completed. A selected-handler harness proves only its declared narrower scope. Do not carry forward any pre-update security conclusion without fresh evidence.

| Case | What to verify | Actual observation and relevant source IDs / HTTP codes | Result | New evidence folder |
|---|---|---|---|---|
| IR-01 | Approved KB relevant for exact Wi-Fi issue | | | `audit/evidence/IR-01/run-.../` |
| IR-02 | Paraphrase retrieves equivalent eligible Wi-Fi evidence | | | `audit/evidence/IR-02/run-.../` |
| IR-03 | Exact technical error code retained and appropriate citation | | | `audit/evidence/IR-03/run-.../` |
| IR-04 | Unknown issue causes safe abstention/escalation | | | `audit/evidence/IR-04/run-.../` |
| IR-05 | Keyword-stuffing does not lead to an unsupported answer | | | `audit/evidence/IR-05/run-.../` |
| IR-06 | Conflicting categories trigger clarification rather than wrong repair | | | `audit/evidence/IR-06/run-.../` |
| IR-07 | Bounded noisy input preserves the correct issue | | | `audit/evidence/IR-07/run-.../` |
| IR-08 | Technical code variants normalized and verified | | | `audit/evidence/IR-08/run-.../` |
| IR-09 | Draft KB excluded from recommendations | | | `audit/evidence/IR-09/run-.../` |
| IR-10 | Trust/source eligibility applied in the actual retrieved list | | | `audit/evidence/IR-10/run-.../` |
| IR-11 | Final solution grounded in the actual cited evidence | | | `audit/evidence/IR-11/run-.../` |
| IR-12 | LOW, UNCERTAIN and HIGH decisions respect the configured thresholds | | | `audit/evidence/IR-12/run-.../` |
| IR-13 | Anonymous agent endpoints deny protected data/function access | | | `audit/evidence/IR-13/run-.../` |
| IR-14 | Verified roles enforce knowledge/admin authorization | | | `audit/evidence/IR-14/run-.../` |
| IR-15 | Malformed input validation, authenticated caller and proven evidence provenance | | | `audit/evidence/IR-15/run-.../` |

## For the individual report

- **Baseline and scope:** Which commit/working tree, fresh data version, configurations, corpus sizes and cached model were used? Did all tests run in the same provider mode?
- **Procedure:** Cite the exact command, requests, isolated database fixture, controls and expected criteria for each case.
- **Evidence:** Capture source IDs/ranks and HTTP response codes; cite new `run-...` directories. Include appropriately redacted screenshots if required by the assignment.
- **Interpretation:** Label the scope of a unit test versus full HTTP test; explain any incomplete/import-limited run.
- **Before vs after:** Compare original report against the new observations separately; never paste the old PASS/FAIL into the new table.
- **Recommendations:** Only propose fixes for issues demonstrated by this current run. Clearly distinguish security problems from environmental/setup failures.
