# IR-10 - Source Reliability / Trust

**Reviewed result: PASS (controlled trust/fallback).** One ticket request completed; the review reads saved evidence without rerunning retrieval. No new security vulnerability demonstrated.

- Test ID: IR-10
- Test Name: Source Reliability / Trust
- Test Objective: Distinguish relevance from source authority and verify documented trust treatment and exclusion of draft/unresolved controls.
- Component Being Tested: _records_from_db(), _deduplicate_records(), BM25Search.scores(), hybrid_rank(), _trust_weight(), _metadata_boost(), search_knowledge(), recommend_solution(), ticket/citation persistence and customer/support output.
- Input / Attack Scenario: Title: Printer queue trust comparison. Description: My printer queue is stuck and print jobs will not clear. One fixed query against an approved KB and resolved historical ticket about the same printer queue issue, with draft/open negative controls.
- Preconditions: Private original backup verified; isolated fixture-only database with two articles and two historical tickets plus synthetic users, snapshotted before request. Distinct positive titles/bodies survive deduplication, same Printers category and Any OS. Original configuration and cached embedding model; Groq disabled.
- Steps: Save criteria/fixtures/input; verify statuses and snapshots; normal CUSTOMER login and one ticket request; capture original corpus, deduplication, native/normalized BM25, semantic/pretrust scores, trust and metadata calls, final results/answer/citations; read IT_SUPPORT queue; verify unchanged fixtures, private snapshot, source and working-DB main-file hashes; stop server; review saved evidence.
- Expected Behaviour: Both positives eligible; actual trust approved=1.0/resolved=0.85; final=pretrust*trust+metadata; draft/open excluded from trusted retrieval/citations. At equal positive pretrust score and equal bonus, approved is higher (derived formula check). More relevant history outranking KB is not automatically a failure.
- Actual Behaviour: Exactly KB and resolved sources eligible and retained. KB normalized BM25=1, semantic=0.6732405449, pretrust=0.8202822997, trust=1, bonus=0.26, final=1.0802822997 (rank 1). History BM25=0, semantic=0.7756518053, pretrust=0.4266084929, trust=0.85, bonus=0.26, final=0.6226172190 (rank 2). Arithmetic residuals zero. Draft/open absent from corpus, rankings and citations; witnesses absent from answer/HTML. Both positives cited; HIGH, SOLUTION_PROPOSED/PENDING; queue absent, unassigned.
- Evidence: [notes.md](notes.md), score_comparison.json/CSV, equal_score_arithmetic.json, review.json and original trust_pair captures.
- Observation: KB already ranked first before trust; historical semantic score is higher. Tiny native BM25 gap becomes normalized 1/0 in this two-document corpus. Equal-score preference is derived arithmetic, not an observed tie trial. Recurring OBS-IR05-02: customer 108% versus explanation 100%.
- Outcome: PASS (controlled trust/fallback) under the predeclared rules.
- Vulnerability Identified: NO demonstrated source-trust violation, draft/unresolved content use or security exploit in this path.
- Impact: No adverse trust-boundary outcome observed. Overstated confidence/provenance wording may mislead; no actual repair, harm or unauthorized access demonstrated.
- Likelihood: Correct treatment observed once for this fixed fixture pair; broader prevalence and other routes unmeasured.
- Severity: No vulnerability severity assigned for this PASS. Recurring confidence-display observation remains Informational on demonstrated security-impact scale.
- Technical Explanation: Database eligibility removes draft/open before ranking. Original hybrid ranking uses 0.45 BM25 and 0.55 semantic; search_knowledge multiplies each shortlisted raw score by trust and adds the same 0.26 bonus. The historical penalty is 0.0639912739; it widens an existing relevance gap without reversing rank.
- Recommended Mitigation: Retain status filtering and trust arithmetic; after approval, use accurate score/provenance wording and assess each included action against the request. Broader corpora, cutoff competition and enabled-provider answers need separate coverage. No application fix applied.
- Conclusion: Documented authority weighting and negative-control exclusion pass for this isolated fallback request. No universal KB-first guarantee, numeric relevance equality or repair validity claimed. IR-11 through IR-15 unexecuted.
- Testing Limitations: Synthetic fixture-only corpus, local development, two eligible sources below top-k=5, no enterprise/real-user deployment, no successful Groq return and no alternate caller tested.

## Exact input, fixtures and runtime

~~~text
Title: Printer queue trust comparison
Description: My printer queue is stuck and print jobs will not clear.
~~~

The 56-character description is identical in stored, masked and canonical fields. Normalized query: `printer queue stuck print jobs will not clear` (8 tokens); no error code or exact-code boost. Title does not determine this retrieval query.

| Fixture ID | Kind / status | Role |
|---|---|---|
| AUDIT-IR10-KB-001 | internal_kb / approved | Positive approved reference |
| AUDIT-IR10-RESOLVED-001 | resolved_ticket / RESOLVED, approval APPROVED | Positive historical case |
| AUDIT-IR10-DRAFT-001 | internal_kb / draft, authoritative=true | Negative source-status control |
| AUDIT-IR10-OPEN-001 | historical ticket / OPEN, approval PENDING | Negative unresolved control, with nonempty provisional notes |

Full fixed titles/bodies/metadata are in fixtures.json and trust_pair/fixture_preflight.json. Positives both describe a stuck printer queue but have distinct bodies/titles. Draft witness `draftmarble612` and open witness `openwillow824` were not submitted in the query. Fixture fields/statuses are unchanged afterward. The original CSV corpus and working-database rows were not copied into this fixture-only database.

Cached all-MiniLM-L6-v2, BM25/semantic 0.45/0.55, HIGH 0.68, UNCERTAIN 0.55, top-k 5, one numerical-library thread. LLM setting llama-3.1-8b-instant; Groq disabled, 2 failed RuntimeError attempts, zero successful returns.

Normal CUSTOMER login: 303 to /home, home 200; health 200; POST http://127.0.0.1:8001/tickets/create returns 303 to /tickets/3; customer page 200. The new isolated ticket is TCK-00003. Normal IT_SUPPORT login 303 and queue page 200; ticket absent, unassigned. The server stopped. Model load 13.39 s; retrieval 0.416 s; process 20.082 s, exit 0, no timeout. No credentials, token values or cookies are recorded.

The original private database backup was verified, and a separate integrity-checked consistent SQLite snapshot of the seeded fixture database was created before the request. Its private path/hash/statuses are recorded in trust_pair/isolated_database_backup.json; the snapshot remains outside the repository and was hash-verified again during review. No working-database edits or source approval changes were made.

## Scores and authority treatment

| Source | Native BM25 | Normalized BM25 | Semantic | Pretrust hybrid | Trust | Metadata | Final | Rank before / after |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| AUDIT-IR10-KB-001 | -0.837840814526 | 1.0 | 0.6732405449 | 0.8202822997 | 1.00 | 0.26 | 1.0802822997 | 1 / 1 |
| AUDIT-IR10-RESOLVED-001 | -0.843967023384 | 0.0 | 0.7756518053 | 0.4266084929 | 0.85 | 0.26 | 0.6226172190 | 2 / 2 |

Native BM25 values were captured from the original BM25Okapi.get_scores return before normalization. The native gap is only 0.0061262089. The original min-max normalization over these two records yields 1 and 0, so normalized zero does not establish irrelevance. The historical ticket has the stronger semantic similarity. This small corpus strongly affects the observed pretrust score gap; it does not isolate authority by equalizing relevance.

`hybrid_rank()` uses 0.45 * normalized BM25 + 0.55 * semantic here, with no exact-code bonus. `_metadata_boost()` contributes category 0.18 plus approved/resolved status 0.08 = 0.26 for each; Any OS contributes no OS bonus. `search_knowledge()` applies pretrust * _trust_weight(record) + _metadata_boost(query, record). Both original adjusted scores match exactly (zero recorded residual).

KB was already first: pretrust gap 0.3936738068, final gap 0.4576650807. The 0.85 weight reduces the historical score by 0.0639912739 relative to weight 1.0. Trust widens the gap but causes no rank reversal. The entire final difference cannot be attributed to authority.

### Equal-score calculation - derived evidence only

`(r * 1.0 + b) - (r * 0.85 + b) = 0.15 * r`. With a common positive pretrust score and common bonus, approved is higher; at r=0 they tie. Both actual pretrust scores here are positive. The following calculations reuse each observed positive value as a hypothetical common score. These are not actual equal-score retrieval results; no score was injected and no additional request was made.

| Common positive r | Equal bonus b | Derived KB | Derived history | Derived advantage |
|---:|---:|---:|---:|---:|
| 0.8202822997 | 0.26 | 1.0802822997 | 0.9572399547 | 0.1230423450 |
| 0.4266084929 | 0.26 | 0.6866084929 | 0.6226172190 | 0.0639912739 |

## Eligibility and provenance

`_records_from_db()` selects approved articles and RESOLVED tickets with nonempty resolution notes. Actual full eligible corpus contains exactly KB and resolved controls, and original deduplication retains both. Draft/open controls are absent before ranking, including the OPEN ticket despite its nonempty provisional notes. Their IDs are absent from rankings/citations and response-only witnesses are absent from the answer and customer HTML. This is stronger evidence than absence from top-k alone.

The separate pure-helper trust preflight returns approved=1.0, resolved=0.85, draft=0.0. Runtime trust calls contain only approved and resolved; no runtime draft-weight branch or open-ticket pure-helper result is claimed. The SQL status filter establishes observed negative-control exclusion. A standalone zero weight alone would not establish exclusion from a caller that also adds metadata.

Trust is applied after the hybrid top-k shortlist. With only two eligible records and k=5, this case tests no shortlist competition or authority-aware cutoff behavior. No alternative direct-hybrid caller, approval-route mutation or every possible source status was exercised.

## Actual fallback answer and stored outcome

~~~text
Evidence source AUDIT-IR10-KB-001 | Printer queue review procedure
For a stuck printer queue, record the waiting print jobs and ask IT Support to review the queue before making changes. Synthetic approved reference for this audit.

Evidence source AUDIT-IR10-RESOLVED-001 | Stalled print jobs reviewed by support
Problem: Printer queue was stuck and print jobs would not clear.
Root cause: Synthetic support case; no verified device diagnosis.
Resolution: Recorded waiting jobs and referred the printer queue to IT Support for review. No device settings were changed.
~~~

Actual explanation:

This recommendation was selected because the issue matched the approved guidance in Printer queue review procedure with 100% relevance, and it aligns with 2 supporting sources that were validated for this workflow.

Actual suggested reply:

Thanks for reporting this issue. Based on the approved guidance in Printer queue review procedure, the recommended next step is to follow the documented troubleshooting steps and confirm the issue is resolved.

Both cited sources address the same queue issue and suggest recording jobs/support review; no device repair was performed or validated. Source types remain internal_kb and resolved_ticket in the citations. The template says validated and asks for confirmation of resolution; these words do not establish real-world validation or a completed repair. Text asking for IT Support review is not automatic escalation or a human response: actual status is SOLUTION_PROPOSED/PENDING and the normal support queue does not show this ticket.

**Recurring OBS-IR05-02:** the actual customer page displays 108% from the unbounded 1.0802822997 ranking score, while explanation text clamps it to 100%. Neither number is a calibrated correctness probability. This is retained as an existing confidence-display/wording observation, not a new primary trust failure or formal security vulnerability.

## Evidence index and reproduction

| Files | Purpose |
|---|---|
| inputs.json / fixtures.json / expected_result.md | Exact predeclared input, fixture design and PASS/FAIL rules |
| preconditions.json / source_preflight.json / comparison_preflight.json | Configuration, original backup and integrity preconditions |
| trust_pair/fixture_preflight.json / isolated_database_backup.json / fixture_postflight.json | Stored fixtures before/after, private snapshot and unchanged statuses |
| trust_pair/analysis.json / query_preprocessing.json | Actual classification/canonical query/tokenization |
| trust_pair/eligible_records.json / eligible_corpus.json / deduplication_preflight.json / deduplication_runtime.json | Full eligibility and retention before scoring |
| trust_pair/native_bm25.json / hybrid_before_trust.json / actual_trust_calls.json / actual_metadata_calls.json / retrieval.json | Original score stages and final ordering |
| trust_pair/trust_preflight.json | Separately labelled pure-helper diagnostics |
| trust_pair/negative_control_checks.json / solution.json / ticket.json | Exclusion, complete answer and persisted provenance |
| trust_pair/customer_result.html / support_queue.html / support_queue_check.json | Actual saved HTTP responses; not screenshots |
| trust_pair/execution.json / terminal_log.txt / process_result.json and root process_result.json | Runtime status, timing, one request, shutdown and integrity |
| score_comparison.json / score_comparison.csv / equal_score_arithmetic.json / review.json / notes.md | Later derived calculations and reviewed verdict |

Already executed; rerunning this command creates new evidence and another temporary database:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir10.py
~~~

Original worker files remain Unassessed/awaiting review to preserve the raw capture; review.json supplies this later PASS. Earlier evidence and all current raw captures are unchanged. Source and working-database main-file hashes match baseline; the main-file hash does not cover unrelated concurrent WAL writes. The runner never writes the working database.

**Conclusion:** documented trust adjustment and draft/unresolved exclusion pass for the controlled local fallback request. No new vulnerability demonstrated. Equal-score preference is arithmetic evidence only. IR-11 through IR-15 remain unexecuted; stop before IR-11.
