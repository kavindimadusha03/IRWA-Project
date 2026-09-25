# IR-08 - Error-Code Formatting Variations

**Outcome: PASS for primary retrieval formatting on an isolated fixture; FAIL for the auxiliary uppercase entity check.** All five variants yielded identical normalized queries, rankings, scores, flags and fallback answers. Uppercase 0X alone was missing from the analysis entity field. No security vulnerability was demonstrated.

## Objective and exact input

Assess case and punctuation tolerance without changing the error-code identity or introducing a formatting-driven unsupported confident answer. All tickets use title `Windows blue screen report` and sentence template `Windows blue screen error {variant}`.

| Subcase | Exact submitted description | Characters |
|---|---|---:|
| lowercase | `Windows blue screen error 0x00000124` | 36 |
| uppercase | `Windows blue screen error 0X00000124` | 36 |
| prefix | `Windows blue screen error error: 0x00000124` | 43 |
| punctuation | `Windows blue screen error 0x00000124!!!` | 39 |
| quoted | `Windows blue screen error "0x00000124"` | 38 |

The prefix variant intentionally produces `error error:` by inserting the whole specified variant into the fixed sentence. All inputs exceed route minimum length and fit below the 180-character canonical limit; masking/truncation changed none. Exact input JSON/text is saved before requests.

## Source prerequisite and controlled fixture

The unchanged original corpus contains zero approved exact-code articles and zero eligible resolved exact-code tickets. Four matching historical tickets are Open without resolution and excluded. IR-03 therefore remains Inconclusive; its evidence was not edited.

The IR-08 plan explicitly permits a labelled isolated fixture. The same article was added to each of five fresh temporary databases containing the original synthetic CSV data. Each actual retrieval corpus has 428 eligible records: the original 427 plus this one fixture. No working-database row or project CSV was modified.

| Fixture field | Value |
|---|---|
| Source ID | AUDIT-IR08-EXACT-001 |
| Title | Synthetic lookup: Windows blue screen 0x00000124 |
| Category | Windows / Updates |
| Status / type | approved / internal_kb |
| Authoritative / OS | false / Any |
| Author | IR-08 synthetic audit fixture |
| Created / updated | 2026-09-22, fixed across copies |

> Synthetic IR-08 lookup fixture for error 0x00000124. This fixture does not establish a diagnosis or a verified repair. Record the displayed code and symptoms and ask IT Support to review them before applying changes.

**Approved is synthetic fixture metadata, not independent approval or verification of a real diagnosis/repair.** This case tests lookup of a code-reference control; it does not repair the missing real knowledge in IR-03. Adding a document changes the corpus and normalization, so IR-08 scores are not a direct comparison with original-corpus IR-03 scores.

All five corpus hashes: `e48e58a54caa9e0a7033d1ed9659647dfbd1d04ef53d7e7c6b75c6129ae2cf8a`. All seven retrieval fields match the original CSV-derived records plus the declared fixture.

## Prior rules, prerequisites and steps

- Primary PASS: all five requests succeed, code identity survives actual retrieval preprocessing, the exact fixture remains eligible/top-k with correct flags, and no formatting-induced unsupported confident transition occurs.
- Primary FAIL: valid formatting variation loses code identity/exact-source relevance, produces wrong flags, crashes or introduces an unsupported confident recommendation. Score changes alone would not fail retained relevance.
- Auxiliary entity check: all equivalent forms should populate entities.error_code consistently after normalization; assess separately because retrieval does not consume this field.
- Verify +0.35 from original raw-score components; no extra search, ablation or altered-score experiment. Inspect generic advice even when formatting parity passes.
- Missing environment/backup/login/corpus prerequisites would mean Not ready/Inconclusive. FAIL does not automatically mean vulnerability. These criteria were saved in expected_result.md before execution.

Existing private Phase 1 backup verified by checksum; application/data/evaluation/test hashes unchanged. Each database has 80 CSV articles plus one fixture and 500 historical tickets. Active synthetic CUSTOMER/IT_SUPPORT users logged in normally. Credentials/cookies/tokens are omitted.

Configuration: cached all-MiniLM-L6-v2, BM25/semantic 0.45/0.55, HIGH=0.68, UNCERTAIN=0.55, top-k=5 and one numerical-library thread. Groq model setting remains llama-3.1-8b-instant; Groq disabled in all five.

1. Saved exact inputs, source gap, fixture and criteria.
2. For each variant, verified the temporary DB path, seeded the original corpus plus fixture and checked stored fields.
3. Started the unchanged app on an owned loopback socket, logged in as CUSTOMER and submitted once.
4. Observed original analysis, normalization, corpus/ranking and solution outputs without changing their arguments or results; saved ticket/citations and actual customer HTML.
5. Logged in as IT_SUPPORT, read the queue, stopped the server and verified source/database hashes.
6. Compared all five original outputs. No approval, rejection, resolution, manual escalation or recommended repair was executed.

Reproduction command (already executed; a rerun creates new evidence and five temporary databases):

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir08.py
~~~

The documented backup command is `python -B audit/scripts/collect_baseline.py backup`, using a read-only SQLite source and private temporary backup. This run verified the existing backup.

Each sequential server used POST http://127.0.0.1:8001/tickets/create and GET /tickets/501. TCK-00501 belongs to a different isolated DB in each run. All five: health 200, CUSTOMER login 303 to /home, home 200, create 303, ticket page 200, IT_SUPPORT login 303 and support page 200. All servers stopped.

## Five-case results

| Variant | Retrieval code / fixture rank | Exact flag | Best score | Decision | Retrieval | Entity / check |
|---|---|---|---:|---|---|---|
| `0x00000124` | 0x00000124 / 1 | true | 1.4439183083 | HIGH | PASS | 0x00000124 / PASS |
| `0X00000124` | 0x00000124 / 1 | true | 1.4439183083 | HIGH | PASS | null / FAIL |
| `error: 0x00000124` | 0x00000124 / 1 | true | 1.4439183083 | HIGH | PASS | 0x00000124 / PASS |
| `0x00000124!!!` | 0x00000124 / 1 | true | 1.4439183083 | HIGH | PASS | 0x00000124 / PASS |
| `"0x00000124"` | 0x00000124 / 1 | true | 1.4439183083 | HIGH | PASS | 0x00000124 / PASS |

Every canonical string retains its original formatting. Both original/canonical-query extraction and normalized-query extraction yield 0x00000124. Normalization yields `windows blue screen error 0x00000124` and five BM25 tokens: windows, blue, screen, error, 0x00000124. The repeated error token in the prefix case is deduplicated; uppercase, quotes and exclamation marks do not change the normalized result.

All complete ranked item dictionaries and solution objects compare exactly equal across all five, including IDs/order, contents, scores, flags and citations. Best-score differences are exactly zero in saved values. This is five controlled observations, not a population accuracy estimate.

## Common ranking

| Rank | Source | BM25 | Semantic | Raw hybrid | Bonus residual | Final score | Exact | Cited |
|---|---|---:|---:|---:|---:|---:|---|---|
| 1 | AUDIT-IR08-EXACT-001 | 1.000000 | 0.698033 | 1.183918 | 0.35 | 1.443918 | true | Yes |
| 2 | SYN-0005 | 0.706947 | 0.633817 | 0.666725 | 0.00 | 0.826717 | false | Yes |
| 3 | SYN-0054 | 0.270311 | 0.382466 | 0.331997 | 0.00 | 0.542197 | false | Yes |
| 4 | SYN-0026 | 0.018430 | 0.398908 | 0.227693 | 0.00 | 0.453539 | false | No |
| 5 | SYN-0135 | 0.254335 | 0.229652 | 0.240759 | 0.00 | 0.284646 | false | No |

Only the synthetic fixture is code-specific. Raw hybrid minus weighted BM25/semantic is 0.35000000000000003 for it and zero for the other returned sources in all five. This observes the positive exact-match branch, which IR-03 could not exercise; it is not a causal rank ablation.

Fixture calculation: `(0.45*1 + 0.55*0.6980332879 + 0.35)*1.0 + 0.18 + 0.08 = 1.4439183083`. Approved-status trust is 1.0 and category/status metadata adds 0.26. Scores are ranking values, not calibrated probabilities.

## Actual answer and applicability

All five answers copy these same three source bodies:

~~~text
Evidence source AUDIT-IR08-EXACT-001 | Synthetic lookup: Windows blue screen 0x00000124
Synthetic IR-08 lookup fixture for error 0x00000124. This fixture does not establish a diagnosis or a verified repair. Record the displayed code and symptoms and ask IT Support to review them before applying changes.

Evidence source SYN-0005 | Blue screen appears after installing an update
Problem: Blue screen appears after installing an update on Windows 10. This started this morning.
Root cause: 
Resolution: Installed pending driver updates and repaired Windows update components.

Evidence source SYN-0054 | Windows driver error after restart
Problem: Windows driver error after restart on Windows 11. No recent hardware changes were made.
Root cause: 
Resolution: Installed pending driver updates and repaired Windows update components.
~~~

The fixture caveat is visibly retained. The two cited historical records contain generic Windows driver/update resolutions and blank root causes. The input gives no OS version, update/restart trigger or confirmed driver fault; applicability of those repairs to this code remains unestablished. Rank-five software-installation evidence is unrelated to the stated fault and not used in the answer.

Actual explanation:

> This recommendation was selected because the issue matched the approved guidance in Synthetic lookup: Windows blue screen 0x00000124 with 100% relevance, and it aligns with 3 supporting sources that were validated for this workflow.

Actual suggested reply:

> Thanks for reporting this issue. Based on the approved guidance in Synthetic lookup: Windows blue screen 0x00000124, the recommended next step is to follow the documented troubleshooting steps and confirm the issue is resolved.

Actual HTML displays 144% retrieval confidence, whereas the explanation clamps to 100%; existing OBS-IR05-02 recurs. Validated-source wording and the follow-troubleshooting reply overstate applicability despite the preserved fixture caution; existing OBS-IR03-01 recurs. All five forms exhibit the same limitation, so it is not a formatting-induced transition or proof of a verified repair.

All tickets: Windows / Updates, Medium priority, SOLUTION_PROPOSED/PENDING, absent from the support escalation queue. Text asking the reader to consult support is not actual application escalation or human acknowledgment. The third cited score is 0.5421971248, below UNCERTAIN 0.55; HIGH uses the best score and includes the first three. This is a recorded selection detail, not a separate threshold experiment. No real device repair occurred.

Each run recorded two RuntimeError failures from llm.chat, zero successful returns and configured_enabled=false. Ten failed local attempts across five cases are not ten successful or rate-limited Groq requests. Only rule/evidence fallback was observed.

## Auxiliary extraction defect and technical explanation

**OBS-IR08-01:** uppercase 0X00000124 alone produced analysis.entities.error_code=null. The other four values are 0x00000124. This FAILS the separately predeclared entity consistency check.

`ERROR_RE` requires lowercase 0x (`app/agents/ticket_agent.py:5`); `_entities()` searches original text (`:42-44`). In contrast, `normalize_query_for_search()` lowercases (`app/services/hybrid_search.py:97`), `_extract_error_codes()` lowercases (`:156`), and `tokenize()` lowercases matched alphanumeric tokens (`app/services/bm25.py:36`). `process_new_ticket()` passes canonical_issue rather than the entity field to `search_knowledge()` (`app/agents/coordinator.py:54`). The entity miss therefore did not affect this actual retrieval/answer path.

## Impact, likelihood, severity and mitigation

- Vulnerability identified: NO demonstrated security vulnerability; no formal VULN entry.
- Observed impact: uppercase diagnostic entity omitted, without ranking or answer change. No access/approval bypass, disclosure, executed repair or harm observed.
- Potential impact: consumers of the missing entity could lose structured context; those consumers were not tested. Unnecessary action from generic advice is plausible but no action was performed.
- Likelihood: one uppercase miss, explained by deterministic regex; prevalence and broader parser robustness unmeasured.
- Severity: Informational on the demonstrated security-impact scale; confirmed correctness defect, no assigned security vulnerability severity or exploit-risk score.
- Recommended mitigation: after approval, share case-insensitive code extraction/canonical entity output and add focused regression coverage. Separately verify action applicability and display ranking scores accurately. No fix applied.

## Evidence, limits and conclusion

Root inputs.json, fixture.json and expected_result.md preserve pre-execution definitions; source_preflight.json, preconditions.json and comparison_preflight.json preserve prerequisites. Each of five subdirectories holds input, stored-fixture preflight, token diagnostics, analysis, preprocessing, eligible corpus, both ranking stages, solution, ticket/citations, customer/support HTML, execution, terminal log and process result. comparison.json/comparison.csv and exact_boost_diagnostics.json contain derived comparisons; review.json is the later verdict.

Saved HTML is an actual HTTP response, not a screenshot. Raw worker state intentionally remains awaiting review; review.json provides the assessment. All prior and raw current evidence remains unchanged. Source/data/evaluation/test and original main-database hashes remain unchanged. Main-file checksums do not cover unrelated concurrent WAL writes; the helper never writes the working database.

The small synthetic corpus and fixture, five forms only, local environment and disabled Groq limit the result. No real diagnostic/repair accuracy, production deployment, other codes/boundaries, approval-workflow security or live LLM behavior is established. IR-03 remains Inconclusive. No IR-09 or later test executed.

**Conclusion:** primary retrieval formatting PASS; auxiliary uppercase entity extraction FAIL. These scoped results do not establish recommendation safety or a security exploit. Stop before IR-09.
