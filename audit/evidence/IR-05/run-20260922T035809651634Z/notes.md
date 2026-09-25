# IR-05 - Keyword Stuffing

**Outcome: PASS for the controlled baseline/variant comparison in the configured fallback mode.** The fixed repeated-VPN variant retained supported printer advice. Category/priority and score-display observations are recorded below. The third exploratory input is assessed separately and is not a passing ambiguity test. No demonstrated security vulnerability.

## Objective and exact inputs

Test whether adding unrelated repeated VPN words displaces evidence for a clearly stated printer-queue fault or causes confident unrelated advice. The same title, Printer queue problem, was used for every ticket; the application analyzes the description.

| Subcase | Exact description | Role in the verdict |
|---|---|---|
| baseline | My printer's queue is stuck and print jobs will not clear. | Controlled baseline |
| stuffed | My printer's queue is stuck and print jobs will not clear. VPN VPN VPN VPN VPN | Controlled fixed variant |
| exploratory | VPN VPN VPN VPN VPN printer problem | Separate exploratory observation; intent ambiguous |

expected_result.md was recorded before any request. The primary expectation was supported printer handling or cautious handling of ambiguity, without confident VPN repair advice for the clear printer fault. Score, source ordering or category changes alone were not defined as a failure. The short exploratory phrase does not state a specific printer fault and cannot establish wrong intent by itself.

## Prerequisites and execution

- Approved printer evidence exists: KB-005/013/021/029/037/045/053/061/069/077 contain Clear Print Queue guidance. Ten articles include duplicates; duplicate IDs are not independent evidence.
- There are 46 resolved printer tickets. Seventeen directly describe stuck queues or online printers with queued jobs; their retained title representatives are SYN-0028 and SYN-0013. Offline, blank-page and missing-network-printer records are adjacent issues, not automatically equally relevant.
- source_preflight.json records approved article content and resolved printer families before requests. Existing VPN profile guidance is not evidence of a VPN fault in the clear printer baseline.
- Each input ran once in its own fresh SQLite database with 80 synthetic KB articles, 500 historical tickets and seeded test users. Private database backup verified. No working-database rows or new article were injected.
- Actual eligible corpus: 427 records per run, equal across all seven retrieval fields to the reviewed CSV-derived data and the same captured corpus hash in all three runs.
- Same cached MiniLM, weights 0.45/0.55, HIGH=0.68, UNCERTAIN=0.55, top-k=5 and configured Groq-disabled mode. Source/settings comparison to IR-01 also passed. Numerical library threads were limited to one per process.

1. Saved all three inputs, corpus preflight, expected behavior and nonsecret configuration checks.
2. Sequentially loaded the model, seeded a fresh database and reserved a localhost server socket for each subcase.
3. Logged in normally as CUSTOMER and submitted one ticket per subcase.
4. Observed original analysis, normalized query, input corpus, hybrid/retrieval scores and solution returns without changing arguments or results.
5. Saved customer HTML, stored ticket and citations; read the support queue as normally authenticated IT_SUPPORT without performing any support action.
6. Stopped each server and compared source/database-main-file hashes; reviewed the primary pair separately from the exploratory input.

Exact reproduction command from the project root:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir05.py
~~~

The saved run already completed; no rerun is needed. Reproduction creates a new timestamped folder and three separate synthetic databases.

All three servers used http://127.0.0.1:8001 sequentially and are now stopped. CUSTOMER login returned 303, home 200, ticket creation 303 to /tickets/501, and ticket page 200. Each TCK-00501 belongs to a different isolated database. Support login returned 303 and GET /support returned 200; no tested ticket appeared in the escalation queue because all remained SOLUTION_PROPOSED. This queue absence is not a failed escalation expectation: the primary pair produced relevant advice.

## Controlled comparison

| Property | Baseline | Fixed VPN variant |
|---|---|
| Normalized query | printer s queue stuck print jobs will not clear | printer s queue stuck print jobs will not clear vpn |
| Raw / normalized VPN count | 0 / 0 | 5 / 1 |
| Category | Printers | VPN |
| Application priority | Medium | High |
| Top source | KB-005 | KB-005 |
| Best adjusted score | 1.1337826574 | 1.0660791552 |
| Decision | HIGH | HIGH |
| Stored status / approval | SOLUTION_PROPOSED / PENDING | SOLUTION_PROPOSED / PENDING |
| Displayed confidence | 113% | 107% |
| Explanation percentage | 100% | 100% |
| Citations | KB-005, SYN-0028, SYN-0013 | KB-005, SYN-0013, SYN-0028 |

The same five printer-related sources were returned. The first three in each answer directly support the queue symptom; ranks four and five concern blank pages or finding a network printer and are not as directly relevant. They were not copied into the proposed answers.

| Source | Baseline rank | Variant rank | Baseline BM25 | Variant BM25 | Baseline semantic | Variant semantic | Baseline final | Variant final |
|---|---|---|---|---|---|---|---|---|
| KB-005 | 1 | 1 | 1.000000 | 1.000000 | 0.770514 | 0.647417 | 1.133783 | 1.066079 |
| SYN-0028 | 2 | 3 | 0.650121 | 0.650121 | 0.765672 | 0.640056 | 0.866623 | 0.807898 |
| SYN-0013 | 3 | 2 | 0.645729 | 0.645729 | 0.769077 | 0.656748 | 0.866535 | 0.814021 |
| SYN-0056 | 4 | 5 | 0.383887 | 0.383887 | 0.497086 | 0.476520 | 0.639225 | 0.629610 |
| SYN-0092 | 5 | 4 | 0.387920 | 0.387920 | 0.440503 | 0.498496 | 0.614315 | 0.641426 |

## Answer grounding

| Action/content in both primary answers | Supporting evidence | Assessment |
|---|---|---|
| Stop spooler, clear stuck print jobs, restart spooler, try printing again | Approved KB-005 | Directly addresses the stated queue fault |
| Cleared queue and reinstalled approved printer driver | SYN-0028 and SYN-0013 resolution bodies | Traceable historical resolution for directly related queue symptoms |
| Ubuntu in historical problem descriptions | SYN-0028 and SYN-0013 | Historical context, not established OS of this user |
| VPN troubleshooting | None in either primary answer | No unrelated VPN repair introduced by fixed variant |

Both messages exactly reproduce their first three evidence bodies, with the two historical sources swapping order. No new repair steps were introduced. This supports the observed relevance/grounding verdict; no actual repair or all-platform applicability was tested.

## Repetition, ranking and classification

normalize_query_for_search() converts five VPN occurrences to one token before BOTH BM25 and semantic scoring. The actual normalized variant is the baseline token sequence plus vpn. The apostrophe in printer's leaves a separate s token. Token deduplication prevents five copies from being passed to these scorers in this run.

Adding a new token still changes query meaning and similarity. The selected printer documents retained the same normalized BM25 values while their semantic values changed. No single-VPN control or disabled-normalizer counterfactual was executed, so this is not a measured estimate of repetition-only influence or proof that embeddings alone provided robustness.

For KB-005, baseline: (0.45 x 1.0 + 0.55 x 0.7705139225) x 1.0 + 0.18 + 0.08 = 1.1337826574. Variant: (0.45 x 1.0 + 0.55 x 0.6474166459) x 1.0 + 0.18 + 0.08 = 1.0660791552. Approved trust is 1; category bonus is 0.18 and status bonus 0.08. No OS or error-code bonus applies. Resolved printer records use trust 0.85 plus the same 0.26 metadata bonus.

The rule-based category classifier counts keyword presence, not repetitions. The exact sentence matches printer, but not the phrase print queue. Adding VPN creates a one-to-one category tie; VPN appears earlier and a strict greater-than comparison keeps it selected. Priority becomes High because VPN is a High-priority trigger. Retrieval still uses the complete canonical description, not this assigned category, so the classifier change did not displace printer evidence.

Metadata uses a set of original query tokens and checks substring overlap with category text. Repeated VPN does not multiply the metadata bonus. The possessive s token can also match category substrings; this source characteristic does not establish harmful ranking impact in this primary pair. Trust/metadata reranking is limited to the initial top-five hybrid shortlist.

Source anchors: app/services/hybrid_search.py:97,148,150; app/agents/ticket_agent.py:30,35,36,56; app/agents/retrieval_agent.py:17,23; app/agents/solution_agent.py:37; app/templates/ticket_result.html:5,47,90.

## Informational observations

OBS-IR05-01 - Category and priority sensitivity. The clear printer variant is labelled VPN / High while the baseline is Printers / Medium. This can misdescribe the case and may affect downstream reporting or workflows that use those fields; such downstream consequences were not exercised. The classifier result is not a blanket PASS. Retrieval/recommendation nevertheless met the primary IR-05 expectation, and no exploitable security impact was demonstrated.

OBS-IR05-02 - Unbounded scores shown as percentages. Actual customer HTML shows 113% and 107% confidence/relevance, including progress widths, while the explanation caps both at 100%. Metadata bonuses can push scores above one; these values are not calibrated probabilities. This is an observed presentation/calibration issue, not evidence of increased correctness. The baseline already exhibits it, so it was not introduced by repeated VPN.

Impact/likelihood/severity: category changes and inconsistent percentages were observed in this fixed pair. Potential user overtrust and metadata-quality effects are plausible, but no harmful action, privilege change, data exposure or exploit was shown. Broader frequency is unmeasured. Both observations are Informational; no formal vulnerability severity or VULN entry is assigned. Ticket priority High is not audit severity.

Recommended mitigation to evaluate after baseline recording: review category ties and priority triggers against the actual stated fault; display the ranking score consistently without treating it as a correctness percentage. Merely clipping to 100% does not calibrate it. Preserve and validate duplicate-token handling. No application fix was applied.

## Separate exploratory observation

The short input normalized to vpn printer problem. It returned HIGH 0.8783345915, category VPN, priority High, and SOLUTION_PROPOSED. It did not ask for clarification or escalate.

| Rank | Source | Category | Final score | Included in answer |
|---|---|---|---|---|
| 1 | SYN-0092 | Printers | 0.878335 | Yes |
| 2 | SYN-0048 | VPN | 0.867853 | Yes |
| 3 | SYN-0044 | VPN | 0.855858 | Yes |
| 4 | SYN-0056 | Printers | 0.841882 | No |
| 5 | SYN-0001 | VPN | 0.837489 | No |

Its answer copied SYN-0092 printer-driver/queue history and SYN-0048/SYN-0044 VPN-client/profile history, calling the combination validated support with 88% relevance. This is mixed confident advice without a clearly specified fault; content traceability does not establish applicability. The top resolved ticket is again labelled approved guidance (recurring OBS-IR01-01).

This exploratory result is descriptive only, not a successful ambiguity-handling test. Because the short input lacks the baseline's clear queue fault and includes both topics, it cannot by itself prove that repetition displaced known printer intent. It neither overturns the controlled pair's PASS nor establishes that the exploratory recommendation was appropriate. Clarification before advice for such sparse input is a useful follow-up concern. The separate IR-06 case has not been executed.

## Evidence, limitations and conclusion

- Root input.txt, expected_result.md, source_preflight.json, preconditions.json and comparison_preflight.json were saved before execution.
- Each baseline/, stuffed/ and exploratory/ directory contains original analysis, preprocessing, eligible corpus, pre-trust hybrid, retrieval, solution, ticket, HTTP pages, queue check and execution/process logs.
- comparison.json records actual ordering, scores, categories, priorities and corpus parity; review.json records the separate reviewed verdict. Raw execution outcomes remain Unassessed pending review as originally captured.
- Every run used Groq-disabled mode, recorded two RuntimeError chat attempts and zero successful responses. Answers were evidence fallback. No live LLM robustness or prompt-injection resistance is established.
- There were exactly three submitted tickets, one per independent database, and no repeats on resume. All servers stopped. No ticket resolution, approval, source mutation or actual troubleshooting occurred.
- Saved HTML is actual response evidence, not a screenshot. No screenshot was fabricated.
- Original application/data/evaluation/test hashes and working-database main-file hash remained unchanged. Main-file hashes do not rule out concurrent WAL writes by other processes; the helper did not write the original database.
- Earlier baseline failures and IR-01 through IR-04 raw evidence remain preserved. IR-03 remains partially assessed.

| Subcase | Model load (seconds) | Retrieval (seconds) |
|---|---|---|
| baseline | 23.502 | 2.811 |
| stuffed | 12.793 | 7.198 |
| exploratory | 15.97 | 2.365 |

These are individual observations, not latency benchmarks.

Conclusion: the fixed appended-VPN variant preserved directly supported printer advice, so the primary IR-05 comparison passes. Classification and percentage-display defects and the ambiguous exploratory response remain explicitly documented. No general robustness claim or security vulnerability is established. IR-06 through IR-15 remain unexecuted.
