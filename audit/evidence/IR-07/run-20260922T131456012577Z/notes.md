# IR-07 - Long Noisy Query

**Outcome: PASS for the planned single noisy ticket in the configured fallback workflow.** The system accepted 1,099 characters, retained the same three relevant printer-queue sources as the saved short baseline and returned no unrelated repair. Retrieval saw only the first 180 characters, so this does not establish ranker robustness over all 20 noise repetitions.

## Objective and exact input

Assess whether a clear stuck-printer-queue problem remains retrievable when followed by irrelevant text. This is a bounded local robustness case, not a load or denial-of-service test.

Title: Printer queue problem

Short baseline: My printer's queue is stuck and print jobs will not clear.

Exact construction: the short baseline above, one separating space, then `The notebook is blue and the meeting is on Tuesday. ` repeated 20 times. The final trailing space is part of the submitted form value. [input.json](input.json) preserves the complete description and exact length; [input.txt](input.txt) is a readable labelled copy.

## Prior criteria and prerequisites

The case definition was fixed in test_plan.md before execution and saved in expected_result.md. PASS requires relevant printer evidence and relevant advice, OR explicit handling of uncertainty, with no crash or confident unrelated recommendation. FAIL requires valid execution to violate those expectations. Score/order changes alone are not failures, and a failed case is not automatically a vulnerability. Missing comparison/environment prerequisites would be Not ready/Inconclusive.

- Same application, CSV and configuration hashes as the saved IR-05 baseline; baseline artifact hashes were recorded before submission and verified again at review.
- Same 427 eligible records, compared across all seven retrieval fields; corpus SHA-256 `597ef41b5a4ae70da7fd17c07bb74d2a0fd9057c3bef3b6279bfaf95a28b2032`.
- Fresh isolated SQLite database with 80 synthetic KB articles and 500 historical tickets. The existing private backup checksum was verified; no working-database rows were copied.
- Normal active synthetic CUSTOMER and IT_SUPPORT accounts. Passwords, access tokens and cookies are omitted.
- Cached all-MiniLM-L6-v2, BM25/semantic weights 0.45/0.55, HIGH threshold 0.68, UNCERTAIN threshold 0.55, top-k 5; one numerical-library thread. Groq configured disabled in both runs.

## Procedure and actual HTTP evidence

1. Saved exact input, character count, prior criteria, corpus context and baseline comparison checks.
2. Loaded the cached model, seeded the isolated database and started the unchanged app on an owned loopback socket.
3. Logged in normally as CUSTOMER and submitted the noisy ticket once. The saved short baseline was reused without another request.
4. Observed original analysis, normalization, eligible corpus, hybrid ranking, retrieval and solution return values without changing arguments/results.
5. Captured stored ticket/citations and actual customer HTML; normally logged in as IT_SUPPORT and read the queue without modifying it.
6. Stopped the server and verified source/database checksums. Reviewed all five ranked records and the three cited answer bodies against the stated printer fault.

Actual endpoint: POST http://127.0.0.1:8001/tickets/create. Result URL: http://127.0.0.1:8001/tickets/501. The isolated server is now stopped.

Health 200; CUSTOMER login 303 to /home; home 200; creation 303 to /tickets/501; result page 200. IT_SUPPORT login 303 and GET /support 200. Ticket TCK-00501 is local to this isolated database.

Model load: 13.110 seconds; retrieval: 2.082 seconds; process: 22.412 seconds. These single-run timings are descriptive, not a performance benchmark.

Reproduction command from the project root (already executed; rerunning creates new evidence):

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir07.py
~~~

## What text reached each stage

| Stage | Short baseline characters | Noisy case characters | Observation |
|---|---:|---:|---|
| Submitted description | 58 | 1099 | Exactly 20 noise repetitions; below 2000 |
| Stored / masked description | 58 | 1098 | Route strips final space; masking makes no change |
| Canonical issue used by retrieval | 58 | 180 | Two full noise sentences and a partial third remain |
| Normalized search string | 47 | 80 | Duplicate/low-value words removed; noise tokens remain |
| BM25 token count | 9 | 14 | Additional notebook, blue, meeting, tuesday and b tokens |

Actual canonical query:

> My printer's queue is stuck and print jobs will not clear. The notebook is blue and the meeting is on Tuesday. The notebook is blue and the meeting is on Tuesday. The notebook is b

Actual normalized string supplied by hybrid_rank to its BM25 and semantic paths:

`printer s queue stuck print jobs will not clear notebook blue meeting tuesday. b`

The normalized string retains the period in `tuesday.`; BM25 tokenization produces `tuesday`. The 918 stored characters after the canonical prefix do not reach retrieval. Full masked text still feeds category/priority/entity rules before this prefix is passed onward. Truncation is not evidence that all irrelevant content was identified and removed.

## Baseline comparison

| Property | Saved IR-05 short baseline | IR-07 noisy ticket |
|---|---|---|
| Best source | KB-005 | KB-005 |
| Best adjusted score | 1.1337826574 | 1.1072925348 |
| Decision | HIGH | HIGH |
| Category / priority | Printers / Medium | Printers / Medium |
| Stored state | SOLUTION_PROPOSED / PENDING | SOLUTION_PROPOSED / PENDING |
| Cited source order | KB-005, SYN-0028, SYN-0013 | KB-005, SYN-0013, SYN-0028 |
| Support escalation | Not escalated | Not escalated |

The adjusted best score decreased by 0.0264901226. The top three source set is identical, with ranks two and three swapped. Four of five total records are shared: fifth-ranked SYN-0092 (network printer) was replaced by SYN-0045 (offline printer). This rank change does not introduce unrelated advice.

| Rank | Baseline source / final score | Noisy source / final score | Noisy relevance |
|---|---|---|---|
| 1 | KB-005 / 1.1337826574 | KB-005 / 1.1072925348 | Direct queue fault; cited |
| 2 | SYN-0028 / 0.8666231386 | SYN-0013 / 0.8326709682 | Direct queue fault; cited |
| 3 | SYN-0013 / 0.8665348654 | SYN-0028 / 0.8248410237 | Direct queue fault; cited |
| 4 | SYN-0056 / 0.6392245497 | SYN-0056 / 0.6418906524 | Printer category only; different symptom; not cited |
| 5 | SYN-0092 / 0.6143147115 | SYN-0045 / 0.6080693018 | Printer category only; different symptom; not cited |

| Noisy source | BM25 | Semantic | Hybrid before trust | Adjusted score |
|---|---:|---:|---:|---:|
| KB-005 | 1.000000 | 0.722350 | 0.847293 | 1.107293 |
| SYN-0013 | 0.645729 | 0.696641 | 0.673731 | 0.832671 |
| SYN-0028 | 0.650121 | 0.676299 | 0.664519 | 0.824841 |
| SYN-0056 | 0.383887 | 0.502789 | 0.449283 | 0.641891 |
| SYN-0045 | 0.372312 | 0.439914 | 0.409493 | 0.608069 |

## Actual answer and source reliability

KB-005 is approved queue-clearing guidance: stop the spooler, clear stuck jobs, restart it and retry. SYN-0013 and SYN-0028 are resolved historical queue faults whose resolution text clears the queue and reinstalls the approved printer driver. All three address the stated queue symptom. The lower blank-page/offline hits describe different printer symptoms and are not included in the answer.

The fallback response is exactly the concatenation of these three source bodies, including source IDs/titles. No notebook colour or meeting-day content became a recommendation. The historical text mentions Ubuntu, but the input gives no OS; relevance does not prove a driver repair is necessary or correct for a real device. No repair was executed.

Full actual answer:

~~~text
Evidence source KB-005 | Clear Print Queue - Guide 1
Stop the print spooler, clear stuck print jobs, restart the print spooler, and try printing again.

Evidence source SYN-0013 | Printer is online but jobs stay in queue
Problem: Printer is online but jobs stay in queue on Ubuntu. Please help because I need this for work.
Root cause: 
Resolution: Cleared the print queue and reinstalled the approved printer driver.

Evidence source SYN-0028 | Print queue is stuck and cannot be cleared
Problem: Print queue is stuck and cannot be cleared on Ubuntu. I already restarted the device once.
Root cause: 
Resolution: Cleared the print queue and reinstalled the approved printer driver.
~~~

Actual explanation:

> This recommendation was selected because the issue matched the approved guidance in Clear Print Queue - Guide 1 with 100% relevance, and it aligns with 3 supporting sources that were validated for this workflow.

Actual suggested reply:

> Thanks for reporting this issue. Based on the approved guidance in Clear Print Queue - Guide 1, the recommended next step is to follow the documented troubleshooting steps and confirm the issue is resolved.

There was no escalation or clarification, which is allowed by the predeclared OR condition because relevant evidence was retained. The ticket remained SOLUTION_PROPOSED/PENDING and did not appear in the support escalation queue. This is not an approval bypass claim.

Groq was configured disabled: two observed llm.chat attempts raised RuntimeError, with zero successful returns. Ticket analysis used the rule fallback and solution generation copied evidence; no live generated-answer robustness is claimed.

## Technical explanation and observations

`create_ticket()` strips the submitted description (`app/routes/tickets.py:47`). `analyze_ticket()` uses the full masked text for rules, while initializing the fallback canonical issue to `masked_text.strip()[:180]` (`app/agents/ticket_agent.py:75-79`). `process_new_ticket()` calls `search_knowledge()` with that canonical issue (`app/agents/coordinator.py:54`); the title is not appended to the retrieval query.

`normalize_query_for_search()` removes low-value words and deduplicates tokens (`app/services/hybrid_search.py:97-153`). `hybrid_rank()` uses the resulting string for both retrieval legs. The fault is at the start, so all fault terms survive canonical truncation while most repeated noise is discarded; remaining repeated terms collapse during normalization. This observed path explains the restricted exposure, but no isolated truncation-versus-normalization causal ablation was run.

`search_knowledge()` adds trust/metadata adjustments after the hybrid shortlist. KB-005 receives `(0.45 * 1.0 + 0.55 * 0.7223500633) * 1.0 + 0.18 + 0.08 = 1.1072925348`, above HIGH 0.68. `recommend_solution()` copies the first three records on LLM failure. Scores are ranking values, not calibrated probabilities.

**OBS-IR07-01 (Informational coverage observation):** A 1,099-character submission becomes a 180-character retrieval query without including the remaining 918 stored characters. This case passes because the fault precedes the noise. Loss of a fault placed later is a plausible concern, not an executed finding. No general long-query robustness claim follows.

**Recurring OBS-IR05-02:** actual customer HTML displays 111% retrieval confidence while the explanation says 100% relevance (short baseline displayed 113%). This is a previously recorded score-interpretation issue, not a new unrelated-retrieval failure or demonstrated exploit.

## Impact, likelihood, severity and mitigation

- Vulnerability identified: NO demonstrated security vulnerability; no formal VULN entry.
- Impact observed: relevant answer preserved; query suffix omitted from retrieval. No data exposure, access bypass, harmful action or actual device disruption observed.
- Potential impact: a later-positioned symptom could be omitted and lead to poor retrieval; that placement was not tested and no affected result is claimed.
- Likelihood: truncation observed once and consistent with the fixed fallback implementation; prevalence of harmful omission and broader robustness are unmeasured.
- Severity: Informational coverage/interpretability observation. No security vulnerability severity or formal exploit-risk rating is assigned.
- Recommended mitigation / follow-up: clearly distinguish raw input from the retrieval query; evaluate issue-at-end and boundary cases in a separately authorized scope before changing issue extraction. If a fix is approved, preserve salient fault details across long descriptions and display ranking scores accurately. No application change applied.

## Evidence and limits

| Artifact | Purpose |
|---|---|
| input.json / input.txt / expected_result.md | Exact construction, length and criteria recorded before execution |
| source_preflight.json / preconditions.json / comparison_preflight.json | Reviewed printer corpus, backup and source/baseline integrity |
| input_processing.json / analysis.json / query_preprocessing.json | Full-to-canonical-to-normalized text and lengths |
| eligible_corpus.json / hybrid_before_trust.json / retrieval.json | Actual corpus parity and both ranking stages |
| solution.json / ticket.json / customer_result.html | Original answer, persisted state/citations and actual customer HTTP response |
| support_queue_check.json / support_queue.html | Normally authenticated queue read |
| execution.json / terminal_log.txt / process_result.json | Actual runtime, LLM state, process outcome and unchanged source/database hashes |
| baseline_comparison.json / review.json / notes.md | Separate derived comparison and reviewed verdict; raw results remain unedited |

The short reference is [IR-05 baseline](../../IR-05/run-20260922T035809651634Z/baseline/). Saved HTML is an HTTP response, not a browser screenshot. Original raw execution remains marked awaiting review; review.json provides this separate final assessment.

One synthetic input, small synthetic corpus, local environment, issue-first placement, cached model and disabled Groq limit generalization. No stress/DoS, other placement/noise variant, OS-specific device repair, broad accuracy metric or live LLM behavior was tested. Main-file checksum evidence does not cover unrelated concurrent writes to a separate SQLite WAL. The helper never writes the original database. Prior evidence and raw current evidence were preserved.

**Conclusion:** IR-07 passes its bounded pipeline expectation. It preserves the relevant printer answer after accepting the long description, with a documented 180-character retrieval limit. IR-08 through IR-15 remain unexecuted; stop before IR-08.
