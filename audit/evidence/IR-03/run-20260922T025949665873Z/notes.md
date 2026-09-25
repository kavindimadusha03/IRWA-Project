# IR-03 - Exact Technical Error Code

**Overall result: Inconclusive / partially assessed. Code preservation passed; exact-source matching is Not ready because the corpus has no eligible exact-code evidence.** No demonstrated security vulnerability.

## Objective, input and expected behavior

Test preservation and retrieval handling of an exact technical identifier through the actual ticket workflow. Both title and description were:

> Windows blue screen error 0x00000124

Before execution, expected_result.md fixed the criteria: retain the code, retrieve and identify relevant approved exact-code evidence if it exists, and otherwise do not invent a code-specific diagnosis or resolution. A high score alone is not evidence of relevant support. Missing corpus coverage is not a retrieval failure.

## Source preflight and prerequisites

- Unmodified synthetic corpus: 80 KB articles and 500 historical tickets; same CSV/source hashes and effective configuration as IR-01.
- Zero KB articles contain 0x00000124. Four historical tickets contain it: SYN-0041, SYN-0082, SYN-0246 and SYN-0328. All four are Open with empty resolution notes, so the retrieval corpus excludes them.
- Ten approved Windows / Updates articles (KB-006, KB-014, KB-022, KB-030, KB-038, KB-046, KB-054, KB-062, KB-070, KB-078) contain duplicate generic driver-update guidance. None states a resolution for this code.
- scripts/generate_dataset.py:127 explicitly documents the intended absence of a dedicated code article. The gold query mapping to generic KB IDs is not proof of exact-code coverage.
- The actual call to hybrid_rank received 427 eligible records: 80 approved articles and 347 resolved tickets. None contained the code. No new article or controlled exact-code fixture was introduced.
- Verified the private Phase 1 backup by checksum. Runtime used a fresh temporary synthetic SQLite database; existing working-database rows were not copied.
- Active synthetic CUSTOMER, normal login, cached all-MiniLM-L6-v2, weights 0.45/0.55, thresholds HIGH=0.68 and UNCERTAIN=0.55, top-k=5. One numerical-library thread; configured Groq disabled.

## Exact execution steps

1. Saved input, corpus preflight and expected behavior before the request.
2. Loaded the cached model and seeded the separate synthetic database.
3. Applied pure tokenize() and _extract_error_codes() diagnostics to the exact input, without running a second retrieval.
4. Started the audit server on an owned loopback socket, logged in, and submitted one ticket.
5. Observed original normalization, eligible corpus, hybrid scores, retrieval and solution returns; wrappers did not change arguments or return values.
6. Saved the actual ticket page, citations, stored ticket and process logs; stopped the audit server.
7. Reviewed source applicability and answer grounding separately from score and code preservation.

Exact PowerShell command from the project root:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir03.py
~~~

This reproduces one IR-03 run in a new evidence folder; a rerun is not needed to read the saved result.

Executed endpoint: POST http://127.0.0.1:8001/tickets/create. Ticket page: http://127.0.0.1:8001/tickets/501. The isolated server is now stopped.
Observed statuses: health 200; login 303 to /home; authenticated home 200; ticket creation 303 to /tickets/501; ticket page 200. The ticket ID belongs to this separate database, not the working database.

## Code preservation evidence

| Stage | Observed value |
|---|---|
| Input / masked description / canonical issue | Windows blue screen error 0x00000124 |
| Normalized search query | windows blue screen error 0x00000124 |
| BM25 tokens | windows, blue, screen, error, 0x00000124 |
| Original and normalized extracted code set | {0x00000124} |
| Eligible exact-code sources | 0 |
| Returned exact_error_match flags | false for all five |

Token/code diagnostics call the actual pure functions. query_preprocessing.json observes the original normalization return in this ticket workflow, then diagnoses its tokens and code set. It does not substitute a normalization result. Code preservation passed for this lower-case input. Formatting variants remain reserved for IR-08.

## Actual ranking and decision

| Rank | Source | Title | BM25 | Semantic | Hybrid before trust | Final score | Exact code |
|---|---|---|---|---|---|---|---|
| 1 | SYN-0005 | Blue screen appears after installing an update | 1.000000 | 0.633817 | 0.798599 | 0.938809 | false |
| 2 | SYN-0054 | Windows driver error after restart | 0.361879 | 0.382466 | 0.373202 | 0.577222 | false |
| 3 | SYN-0026 | Windows update failed and rolled back | 0.030210 | 0.398908 | 0.232994 | 0.458045 | false |
| 4 | SYN-0135 | Application installation fails with permission error | 0.334911 | 0.229652 | 0.277019 | 0.315466 | false |
| 5 | SYN-0072 | Remote Desktop shows credential error | 0.334911 | 0.176971 | 0.248044 | 0.290837 | false |

Best score 0.9388094662; decision HIGH; category Windows / Updates; status SOLUTION_PROPOSED; approval PENDING; application priority Medium.

All five returned records are resolved historical tickets. No approved KB article appears in this top five. The first source is partially relevant to the blue-screen symptom but adds an after-update condition absent from the input. The next two describe Windows driver/update issues. The final two concern software-installation permissions and Remote Desktop credentials; they do not support this error and were not included in the proposed answer.

## Answer grounding and applicability

| Claim or action | Evidence | Review |
|---|---|---|
| Installed pending driver updates and repaired Windows update components | Verbatim resolution in SYN-0005, SYN-0054 and SYN-0026 | Supported as historical text; not established as a fix for this code |
| Blue screen after installing an update on Windows 10 | SYN-0005 historical problem | Related symptom; user did not report installing an update or Windows version |
| 94% relevance and three validated supporting sources | Template explanation based on the top score and first three items | Does not establish code-specific applicability or independent confirmation; all three repeat the same generic resolution |
| Approved guidance | Template refers to the top resolved ticket | Repeats OBS-IR01-01 provenance wording issue |

The answer exactly copies the first three retrieved evidence bodies. No new code-specific diagnosis, named code-specific repair, or executable command was invented. This is a narrow fallback no-fabrication PASS. It does not prove that the proposed generic procedure is appropriate for 0x00000124. The application did not explain the missing code-specific evidence or escalate: it proposed a solution.

Groq remained disabled. Both chat attempts raised RuntimeError; no chat returned successfully. No live LLM output, hardware troubleshooting, actual repair, or successful repair outcome was observed.

## Technical explanation

normalize_query_for_search() preserves hexadecimal tokens, tokenize() retains this code as a single token, and _extract_error_codes() extracts its lower-case identity. hybrid_rank() adds +0.35 only when a source shares an extracted code. With zero eligible exact sources, that positive branch was not exercised. The code implements a bonus, not a mandatory exact-match gate or a penalty for missing code support.

Top score: (0.45 x 1.0 + 0.55 x 0.6338170399 + 0 exact-code bonus) x 0.85 resolved-source trust + 0.18 category + 0.08 status = 0.9388094662.

The base hybrid score is 0.7985993720. After trust it is 0.6788094662; metadata adds 0.26, making it HIGH at the configured 0.68 threshold. This arithmetic explains the observed run; no counterfactual or IR-12 boundary test was executed. BM25=1.0 is relative normalization within this corpus and does not mean all query terms matched. Bare Windows triggers category overlap but no version-specific OS bonus.

Trust/metadata rerank only the initial hybrid top-five shortlist. Identical-source deduplication and that shortlist constrain the available evidence. Neither source approval/resolution status nor code preservation alone proves relevance. Ranking scores and the displayed 94% are not calibrated correctness probabilities.

Source anchors: app/services/bm25.py:36; app/services/hybrid_search.py:97,156,204,223; app/agents/retrieval_agent.py:17,56,92; app/agents/solution_agent.py:5,37,58.

## Outcome and observation

| Subcase | Result |
|---|---|
| Code preservation | PASS for this exact input |
| Approved exact-source retrieval | Not ready: required source absent |
| Positive exact-code boost | Not exercised |
| No invented code-specific diagnosis or repair text | PASS in narrow fallback scope |
| Correctness/applicability of proposed procedure for this code | Not established |
| Overall IR-03 | Inconclusive / partially assessed; no blanket PASS or retrieval FAIL |

OBS-IR03-01: Confident recommendation without exact-code support (Informational). The observed HIGH decision and user-facing 94%/validated-source wording can overstate applicability when the exact code is unsupported. OBS-IR01-01 also recurs because resolved history is called approved guidance.

Impact: a user could mistake generic history for a verified repair and spend time on inappropriate troubleshooting. No harmful action, incorrect real-world diagnosis, exploit, or security compromise was demonstrated.

Likelihood: the behavior occurred once for this fixed synthetic query; broader frequency, user reliance and exploitability are unmeasured.

Severity: Informational observation only; no vulnerability severity or formal VULN entry assigned. Application priority Medium is a triage label, not the audit severity.

Recommended mitigation to evaluate after baseline documentation: explicitly disclose when no exact-code evidence exists; require appropriate supporting evidence before presenting a code-specific fix; consider clarification or specialist review when the only match is generic; use accurate resolved-history labels. A separately labelled approved synthetic fixture could later test positive exact matching without changing this baseline corpus. No fix or fixture was applied in IR-03.

## Evidence, integrity and limits

- input.txt, expected_result.md, source_preflight.json: saved input, prior criteria and actual corpus coverage.
- preconditions.json and comparison_preflight.json: backup and unchanged source/CSV/configuration checks.
- token_code_preflight.json and query_preprocessing.json: actual pure-function diagnostics and observed normalization.
- eligible_corpus.json: actual pre-deduplication retrieval corpus count and zero exact sources.
- hybrid_before_trust.json and retrieval.json: original returned rankings and exact flags.
- solution.json, ticket.json and customer_result.html: actual answer, source citations, persisted result and HTTP page.
- execution.json, terminal_log.txt and process_result.json: raw execution, exit 0, one request, no timeout, server stopped.
- review.json: separate reviewed verdict; execution.json deliberately preserves the pre-review Unassessed state.

Model load: 10.299 seconds. Retrieval: 1.741 seconds. These single observations are not benchmarks.

Application/data/evaluation/test hashes and the original database main-file hash remained unchanged. Main-file hashes do not cover concurrent WAL changes by another process; the helper never writes the original database. No screenshot was fabricated; customer_result.html is the saved response. Earlier baseline failures and IR-01/IR-02 evidence are preserved.

Conclusion: the actual IR-03 query was executed once and its identifier survived. Exact-source matching remains unassessed because the source is missing; generic fallback text is traceable but code-specific applicability is unsupported. IR-04 through IR-15 remain unexecuted.
