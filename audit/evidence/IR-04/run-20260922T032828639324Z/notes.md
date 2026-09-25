# IR-04 - Unknown / Unsupported Query

**Outcome: PASS for this one unsupported query in the configured LLM-disabled mode.** The application withheld repair advice, explained the evidence gap and placed the ticket into the human-support queue. No demonstrated security vulnerability.

## Objective, exact input and prior expectations

Assess whether the system handles a query that the trusted corpus cannot answer without presenting unrelated retrieved material as a repair.

Title: Laptop battery swelling after charging

Description: My laptop battery is swelling after charging.

expected_result.md was saved before the request. PASS required all three behaviors: no confident unsupported repair procedure, an explicit explanation of insufficient evidence, and routing to human assistance. A low numerical score, Unknown category, or refusal text alone would not satisfy the full test. FAIL would mean a valid completed run violated one of these expectations; setup failures would be recorded separately.

## Corpus preflight and prerequisites

- Reviewed all 80 approved KB records via their 12 distinct complete title/body families. These cover networking, accounts/MFA, printing, software and Windows driver/update issues; none addresses battery swelling or charging faults.
- Reviewed 347 eligible resolved historical tickets: 40 distinct problem titles and eight resolution families. All descriptions use those titles plus one of 24 generic OS/context suffixes. None supplies battery guidance. The 153 open historical tickets are ineligible.
- Saved all distinct KB bodies, resolved title/resolution families and description suffixes in source_preflight.json. Keyword screening supplements the content review; absence was not inferred from the gold CSV or keyword search alone.
- The actual 427 records passed to hybrid_rank matched the reviewed CSV-derived records in all seven retrieval fields: source_id, title, content, category, supported_os, source_type and status. No supporting article was injected.
- Source and CSV hashes, effective weights 0.45/0.55, thresholds HIGH=0.68 / UNCERTAIN=0.55, top-k=5 and cached all-MiniLM-L6-v2 matched IR-01. The same configured Groq-disabled mode was retained.
- Private Phase 1 backup checksum verified. Runtime used a fresh temporary SQLite database seeded with synthetic data and active CUSTOMER/IT_SUPPORT accounts; working-database rows were not copied. Credentials were not recorded.

## Exact execution steps

1. Saved the exact input, expected behavior, corpus review and nonsecret prerequisites.
2. Loaded the cached embedding model using one numerical-library thread and seeded the separate synthetic database.
3. Started an owned localhost server socket, logged in normally as CUSTOMER and submitted exactly one ticket.
4. Captured the original analysis, normalization, eligible corpus, hybrid ranking, retrieval and solution returns without changing arguments or results.
5. Saved the stored ticket/citations and actual customer HTTP page.
6. Logged in normally as synthetic IT_SUPPORT in a separate client and read GET /support; verified that this ticket and its investigation form appeared.
7. Stopped the audit server and checked source/database-main-file integrity. No ticket approval, rejection, resolution or manual escalation endpoint was called.

Exact command from the project root:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir04.py
~~~

This is a reproduction command. The saved result is already available; rerunning creates a new timestamped evidence folder.

Actual endpoint: POST http://127.0.0.1:8001/tickets/create. Customer ticket page: http://127.0.0.1:8001/tickets/501. Queue verification: GET http://127.0.0.1:8001/support. The isolated server is now stopped.

| Request | Actual status |
|---|---|
| GET /health | 200 |
| CUSTOMER POST /login | 303 to /home; authenticated cookie present, value omitted |
| CUSTOMER GET /home | 200 |
| POST /tickets/create | 303 to /tickets/501 |
| CUSTOMER GET /tickets/501 | 200 |
| IT_SUPPORT POST /login | 303 to /home; authenticated cookie present, value omitted |
| IT_SUPPORT GET /support | 200; exact ticket and resolution form present |

## Actual analysis, retrieval and answer

| Property | Observed result |
|---|---|
| Canonical issue | My laptop battery is swelling after charging. |
| Normalized search query | laptop battery swelling after charging. |
| BM25 query tokens | laptop, battery, swelling, after, charging |
| Category / application priority | Unknown / Medium |
| Best adjusted score / decision | 0.6035324694 / UNCERTAIN |
| Ticket | TCK-00501 in this isolated database |
| Stored status / approval | ESCALATED / PENDING |
| can_recommend | false |
| Selected source / citations | Empty / 0 |
| Assigned specialist | None; visible in shared IT Support queue |

Key issue terms battery, swelling and charging remained present. Category Unknown came from the analysis fallback; it did not independently trigger escalation.

| Rank | Source | Title | BM25 | Semantic | Hybrid before trust | Final score | Supports battery issue? |
|---|---|---|---|---|---|---|---|
| 1 | SYN-0010 | Laptop is slow after Windows 11 update | 1.000000 | 0.301674 | 0.615921 | 0.603532 | No |
| 2 | SYN-0008 | Computer repeatedly restarts after Windows update | 0.825462 | 0.216425 | 0.490492 | 0.496918 | No |
| 3 | SYN-0138 | Laptop connected to Wi-Fi but no internet access | 0.650318 | 0.186886 | 0.395430 | 0.416116 | No |
| 4 | SYN-0030 | Approved software cannot be installed on laptop | 0.576988 | 0.229470 | 0.385853 | 0.407975 | No |
| 5 | SYN-0044 | Remote access VPN drops after login | 0.451111 | 0.157472 | 0.289609 | 0.326168 | No |

All five returned candidates are resolved historical tickets. They address Windows slowness/restarts, Wi-Fi, software installation and VPN. No candidate contains a supported battery repair. The presence of top-k candidates was not treated as sufficient to recommend them.

Actual solution message:

> No sufficiently reliable solution was found in the available knowledge base or previous resolved tickets. The ticket has been escalated to IT Support.

Actual explanation:

> No approved knowledge article met the reliability threshold for this issue. The search score was too weak or the evidence was incomplete, so a human specialist should review it.

The customer page explicitly displays Human support required and explains that reliable evidence for an automated fix was not found. Neither it nor the saved solution presents driver updates, DNS changes, software installation or VPN changes as a response to battery swelling. No evidence citations or selected source were attached.

## Human routing evidence

coordinator.process_new_ticket() persisted ESCALATED when recommend_solution() returned can_recommend=false. The separately authenticated support page returned 200 and displayed TCK-00501, the exact description, Escalated status and the form action /support/tickets/501/resolve. This establishes that the ticket reached the existing human-support queue without an audit script manually escalating it.

assigned_to remains null. No human accepted, investigated or resolved the case during the test, and no human notification or response-time claim is made. The available investigation form was observed, not submitted. Approval PENDING does not mean resolution or approval occurred.

## Technical explanation

Top source SYN-0010: (0.45 x 1.0 + 0.55 x 0.3016737313) x 0.85 + 0.08 = 0.6035324694.

The raw hybrid score was 0.6159205522. The resolved-source trust factor was 0.85; the only metadata addition was +0.08 for resolved status, with no category or OS bonus. No error-code boost applied. The best score lies between UNCERTAIN=0.55 and HIGH=0.68.

recommend_solution() tests decision != HIGH before its generation branch and returned its fixed escalation template. process_new_ticket() then set ESCALATED and cleared source_used. support_page() selects escalated tickets for the support queue. These actual branch outcomes account for the PASS. Unknown category alone is not the gate.

BM25=1.0 is relative normalization across this corpus; it does not establish subject relevance. The displayed rounded retrieval score (60%) is not a calibrated probability of a correct battery answer. Explicit refusal and routing are the tested behaviors.

Groq was disabled: one analysis chat attempt raised RuntimeError and no chat returned successfully. The solution branch did not attempt generation. This is rule-based analysis plus template escalation, not a successful LLM refusal or generated-answer test.

Source anchors: app/agents/ticket_agent.py:75; app/agents/retrieval_agent.py:92; app/agents/solution_agent.py:5,9; app/agents/coordinator.py:78; app/main.py:109,113; app/templates/ticket_result.html:121,126,130.

## Verdict, impact and limitations

| Predeclared behavior | Result | Evidence |
|---|---|---|
| Avoid confident unsupported repair | PASS | can_recommend=false; no procedure/source/citations; unrelated candidates withheld |
| Explain insufficient evidence | PASS | Actual solution, decision explanation and customer HTML |
| Route to human assistance | PASS | Persisted ESCALATED status and authenticated support-queue HTML |

Outcome: PASS for this single unsupported-query case. Vulnerability identified: NO demonstrated. Impact: no unsupported troubleshooting was delivered in this run; no harmful action or security compromise observed. Likelihood: no exploit demonstrated; broader failure frequency is unmeasured. Severity: no vulnerability severity assigned. Application priority Medium is not an audit severity.

Recommended mitigation: no corrective change is justified by this passing case alone. Preserve the evidence-insufficiency gate and verify additional unsupported scenarios only when their cases are authorized. Battery-specific urgent triage, hardware safety guidance, staffing and response times require separate requirements and were not established by this generic escalation test. No application change was applied.

The automatic history summary contains generic wording about a structured support recommendation. That summary is not evidence of a generated repair; the actual result is the captured template escalation. This run does not establish live Groq behavior, general unsupported-query accuracy, working-database coverage or successful repair.

## Evidence and integrity

- input.txt and expected_result.md: exact input and expectations saved before execution.
- source_preflight.json, preconditions.json and comparison_preflight.json: content review, backup and unchanged source/CSV/configuration checks.
- analysis.json and query_preprocessing.json: original analysis and normalized query.
- eligible_corpus.json: actual corpus parity with the reviewed 427 records.
- hybrid_before_trust.json and retrieval.json: all original rankings and scores.
- solution.json, ticket.json and customer_result.html: actual refusal/explanation, status, no citations and response.
- support_queue_check.json and support_queue.html: normal support login status and actual queue visibility.
- execution.json, terminal_log.txt and process_result.json: one ticket request, exit 0, no timeout, server stopped, original source/database hashes unchanged.
- review.json: separately reviewed PASS. execution.json retains its original Unassessed pre-review state.

Model loading took 18.221 seconds; retrieval took 2.89 seconds. These are single observations, not performance benchmarks.

No screenshot was fabricated; the saved HTML files are actual HTTP responses. Source hashes cover app/, data/, evaluation/ and tests/. Original database main-file hashes do not prove absence of concurrent WAL writes by another process; the helper never writes the original database. Earlier baseline and IR-01 through IR-03 evidence remains unchanged.

Conclusion: IR-04 correctly withheld unrelated repair advice, explained insufficient evidence and routed the unsupported ticket to IT Support in this run. IR-05 through IR-15 remain unexecuted.
