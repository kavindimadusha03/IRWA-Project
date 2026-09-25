# IR-02 - Paraphrased Query Retrieval

**Outcome: PASS for this single paraphrase through the full retrieval/evidence-fallback workflow.** No security vulnerability is demonstrated by this case.

## Why and what we tested

IR-01 established retrieval for a directly worded Wi-Fi/no-internet issue. IR-02 changes the description while preserving its meaning, to check whether relevant evidence and supported advice remain available.

Title: Wireless connected but websites will not load

Description: My wireless connection shows connected but websites will not load.

The expected_result.md was written before execution. Source order and numeric scores were allowed to change; a category label or HIGH score alone was not sufficient. The same approved KB and resolved-ticket sources remained eligible.

## Preconditions and exact steps

- Compared application/data/evaluation/test source hashes and both CSV hashes with IR-01: unchanged.
- Verified the recorded private backup by checksum; original working-database rows were not used as runtime fixtures.
- Used a fresh temporary SQLite database seeded from 80 synthetic KB articles and 500 historical tickets.
- Loaded the same cached MiniLM model, with one numerical-library thread; weights 0.45/0.55, thresholds 0.68/0.55 and top-k 5 matched IR-01.
- Confirmed the same Groq mode: disabled. No key or credential value was recorded.
- Started a server on a reserved loopback socket, logged in normally as the seeded synthetic CUSTOMER, then submitted exactly one ticket.
- Observed original normalization, hybrid, retrieval and solution return values without altering arguments or results.
- Saved the actual HTTP ticket page, stopped the audit server, and checked source/original-database main-file hashes.

Exact command used in the project PowerShell terminal:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir02.py
~~~

This is a reproduction command, not a request to repeat the case. Any rerun creates a new evidence directory.

Actual page/endpoint during execution: http://127.0.0.1:8001/home -> POST http://127.0.0.1:8001/tickets/create. Ticket URL: http://127.0.0.1:8001/tickets/501. The isolated server is now stopped.

Observed HTTP results: login 303 to /home; home 200; ticket submission 303 to /tickets/501; ticket page 200.

## Actual comparison

| Property | IR-01 | IR-02 |
|---|---|---|
| Top source | SYN-0138 | SYN-0027 |
| Best adjusted score | 0.9441488885 | 0.8240901608 |
| Decision | HIGH | HIGH |
| Category | Wi-Fi / DNS | Wi-Fi / DNS |
| Ticket status | SOLUTION_PROPOSED | SOLUTION_PROPOSED |
| Approval | PENDING | PENDING |
| Application triage priority | Critical | Medium |
| Groq | Disabled; fallback | Disabled; fallback |

| IR-02 rank | Source | IR-01 rank | Type/status | BM25 | Semantic | Adjusted score |
|---|---|---|---|---|---|---|
| 1 | SYN-0027 | 5 | resolved_ticket / resolved | 1.000000 | 0.773455 | 0.824090 |
| 2 | KB-001 | 3 | Internal KB / approved | 0.180360 | 0.566220 | 0.472583 |
| 3 | SYN-0033 | 2 | resolved_ticket / resolved | 0.232373 | 0.624905 | 0.461026 |
| 4 | SYN-0138 | 1 | resolved_ticket / resolved | 0.230227 | 0.608191 | 0.452391 |
| 5 | SYN-0037 | 4 | resolved_ticket / resolved | 0.110686 | 0.571516 | 0.389521 |

All five sources from IR-01 remain in the top five. SYN-0027 directly describes a wireless icon showing connected while websites do not load. KB-001, now second, contains the approved DNS-cache recovery guidance. The other resolved tickets describe the same symptom.

The diagnostic top_in_pre_reviewed_relevant_KB_set=false is not a failure: the top result is an eligible resolved historical ticket, and the planned expectation does not require a KB article to rank first.

## Query preprocessing and limits on semantic claims

Actual canonical issue: My wireless connection shows connected but websites will not load.

Actual normalized query: wifi connection shows connected but websites will not load

The captured normalization maps wireless to wifi and removes the filler my. BM25 and embeddings both receive that normalized query. The leading source's wording is also very close to the paraphrase and has normalized BM25 1.0. Therefore success cannot be attributed to embeddings alone. It demonstrates this combined pipeline's handling of this particular paraphrase.

## Grounding review

| Displayed action/content | Supporting retrieved evidence | Assessment |
|---|---|---|
| Restart network adapter and flush DNS, described as historical resolution | SYN-0027 and SYN-0033 | Present verbatim in resolved-ticket bodies for the same symptom |
| Run ipconfig /flushdns; reconnect to Wi-Fi and test | KB-001 | Present verbatim in the approved article |
| Windows 10 and Windows 11 contexts | SYN-0027 and SYN-0033 respectively | Historical source contexts, not new claims about this customer's device |

The configured LLM was disabled: two attempts raised RuntimeError and no chat returned successfully. The final answer copies the first three evidence bodies. No novel troubleshooting steps were added. This establishes fallback evidence support, not live generated-answer correctness. The user's OS is unspecified; no platform-specific applicability or actual repair success is established.

## Technical explanation and observations

Top score: (0.45 x 1.0 + 0.55 x 0.7734548893) x 0.85 + 0.08 = 0.8240901608. This exceeds HIGH=0.68.

OBS-IR02-01 (Informational scoring-consistency observation): metadata boosting checks the original canonical query, not the query produced by normalize_query_for_search(). The original wireless phrasing lacks the literal category-token match that gave IR-01 +0.18. Both cases receive +0.08 for approved/resolved status; IR-01's total metadata bonus was +0.26, while IR-02's is +0.08. Evidence: query_preprocessing.json, captured scores and app/agents/retrieval_agent.py:17-40,94-110.

Impact: equivalent wording can alter confidence through the metadata bonus as well as changing lexical/semantic scores. Both actual cases remained HIGH and relevant, so no harmful decision or exploitable vulnerability is established here. Likelihood: demonstrated for this pair only; broader frequency and threshold effects remain unmeasured.

Recommended mitigation to evaluate later: normalize query terms and category labels consistently, then validate confidence decisions against labelled cases. Feeding only a normalized query into the unchanged category matcher is not necessarily sufficient because category token spelling/spacing also matters. No fix was applied.

OBS-IR01-01 recurs: the explanation calls resolved-ticket SYN-0027 approved guidance. This repeats the existing Informational provenance wording observation, not a new vulnerability. Prefer source-aware wording after documenting baseline behavior.

The application triage priority changed from Critical in IR-01 to Medium in IR-02. The rule-based classifier's literal no internet trigger occurs only in IR-01. This is a triage observation outside the IR-02 relevance verdict, and those words are not audit vulnerability severities.

The lower final score does not mean a measured reduction in correctness. Ranking scores are not calibrated probabilities.

## Evidence and scope

- input.txt and expected_result.md: exact input and predeclared criteria.
- comparison_preflight.json: same-source and same-CSV checks.
- source_preflight.json and preconditions.json: source bodies, hashes and backup verification.
- query_preprocessing.json: exact captured original/normalized query.
- hybrid_before_trust.json and retrieval.json: actual original return values.
- solution.json, ticket.json and customer_result.html: actual fallback, citations, stored status and HTTP response.
- execution.json and terminal_log.txt: raw observations; worker verdict remained Unassessed until this separate review.
- process_result.json: one ticket, exit 0, original database main file and source hashes unchanged.
- comparison.json and review.json: reviewed comparison and scoped PASS.

Model-loading preflight: 13.56 seconds. Retrieval with model already loaded: 2.157 seconds. These are single observations, not a cache benchmark.

No screenshot was fabricated; customer_result.html is a captured response. The two /tickets/501 IDs belong to different isolated databases, not the same persisted ticket or original working database.

Conclusion: IR-02 passes within the single-query hybrid/fallback scope. IR-03 through IR-15 remain unexecuted. Phase 1 test-suite/evaluation failures and IR-01 evidence are preserved.
