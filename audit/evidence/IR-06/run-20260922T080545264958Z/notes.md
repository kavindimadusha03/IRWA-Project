# IR-06 - Conflicting Category Keywords

**Outcome: FAIL for the predeclared ambiguity-handling expectation in this single fallback-mode run.** The application offered a confident mixed RDP/VPN recommendation without clarifying the fault, acknowledging ambiguity or escalating. This establishes an answer-reliability defect; it does not by itself establish a security vulnerability.

## Objective, input and expected behavior

Test whether an underspecified query spanning several categories receives cautious handling before a repair is presented as applicable.

Title: Connection issue across services

Description: Wi-Fi VPN Outlook printer DNS remote desktop cannot connect

Before execution, source_preflight.json recorded that no single fault was confirmed. The input names Wi-Fi/DNS, VPN, Outlook, a printer and Remote Desktop, followed by cannot connect. It does not establish which operation fails, the operating system, error message, root cause or sequence of events. There is no independently correct category label to manufacture.

Expected behavior, fixed in expected_result.md before the request: acknowledge ambiguity, ask for useful clarification or escalate; do not present an unsupported diagnosis or repair as established. A matching category, source citation or HIGH score alone is insufficient. The alternatives are OR conditions; the test does not require escalation if adequate clarification occurs.

## Preconditions and procedure

- Verified private Phase 1 backup checksum and unchanged application/data/evaluation/test source hashes.
- Used a fresh isolated SQLite database with 80 synthetic KB articles, 500 historical tickets and active synthetic CUSTOMER/IT_SUPPORT users. Working-database rows were not copied.
- Captured distinct approved article and resolved-ticket title/resolution families before execution. These contain guidance for several named topics, but topic overlap does not establish a fault.
- Actual 427 eligible records exactly matched reviewed CSV-derived records in all seven retrieval fields. Corpus/settings matched IR-01; no source or score was injected.
- Same cached all-MiniLM-L6-v2, weights 0.45/0.55, thresholds HIGH=0.68 / UNCERTAIN=0.55 and top-k=5; one numerical-library thread. Groq remained configured disabled.

1. Saved the exact input, prior criteria, corpus context and prerequisites.
2. Loaded the cached model, seeded the separate database and started the server on an owned loopback socket.
3. Logged in normally as CUSTOMER and submitted one ticket.
4. Observed original analysis, normalization, corpus, hybrid ranking, retrieval and solution return values; wrappers changed no arguments or results.
5. Saved ticket/citations and the actual customer HTTP page; normally logged in as IT_SUPPORT and read the support queue.
6. Stopped the server, checked integrity and reviewed applicability separately from source traceability. No recommendation, approval, rejection, resolution or manual escalation action was executed.

Exact reproduction command from the project root:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir06.py
~~~

This saved run has already completed. A rerun would create a new evidence folder; it is not needed to read the result.

Actual endpoint: POST http://127.0.0.1:8001/tickets/create. Ticket URL: http://127.0.0.1:8001/tickets/501. Queue check: GET http://127.0.0.1:8001/support. The isolated server is stopped.

HTTP observations: health 200; CUSTOMER login 303 to /home; home 200; ticket submission 303 to /tickets/501; ticket page 200; IT_SUPPORT login 303 and support page 200. Ticket TCK-00501 belongs to this isolated database.

## Actual classification and result

| Property | Observed result |
|---|---|
| Canonical issue | Wi-Fi VPN Outlook printer DNS remote desktop cannot connect |
| Normalized query | wifi vpn outlook printer dns remote desktop cannot connect |
| Category | Wi-Fi / DNS |
| Application priority | High |
| Extracted application / device / OS | Outlook / desktop / unspecified |
| Best score / decision | 0.8604451667 / HIGH |
| can_recommend | true |
| Stored status / approval | SOLUTION_PROPOSED / PENDING |
| Selected source | SYN-0070 |
| Citations | SYN-0070, SYN-0044, KB-008 |
| Clarification or explicit ambiguity caveat | None in the reviewed response |
| Escalation queue | Ticket absent; no support resolution form for it |

Wi-Fi / DNS wins the fallback category count because wi-fi and dns give two distinct keyword matches. VPN, Outlook, printer and remote desktop each provide a category cue. The rule selects a label without resolving the underlying uncertainty. Entity extraction also reflects keyword order, not verified device/application facts. Classification alone is not the failure; the unqualified recommendation is.

## Retrieved evidence

| Rank | Source | Category / status | BM25 | Semantic | Hybrid before trust | Final | Cited |
|---|---|---|---|---|---|---|---|
| 1 | SYN-0070 | Remote Desktop / resolved | 1.000000 | 0.466193 | 0.706406 | 0.860445 | Yes |
| 2 | SYN-0044 | VPN / resolved | 0.481611 | 0.469050 | 0.474702 | 0.663497 | Yes |
| 3 | KB-008 | Remote Desktop / approved | 0.484437 | 0.336647 | 0.403152 | 0.663152 | Yes |
| 4 | SYN-0092 | Printers / resolved | 0.440133 | 0.391907 | 0.413609 | 0.611567 | No |
| 5 | SYN-0048 | VPN / resolved | 0.274826 | 0.498519 | 0.397857 | 0.598178 | No |

These sources overlap named topics. They do not independently establish that an RDP rule, saved credentials or VPN profile is the cause of this request. The system copied the first three after reranking; no new repair text was generated.

| Proposed content | Source traceability | Applicability to this request |
|---|---|---|
| Enabled approved RDP rule and checked reachability | Verbatim historical resolution in SYN-0070 | RDP is mentioned, but no rule/reachability fault or Ubuntu system is confirmed |
| Updated VPN client and re-created profile | Verbatim historical resolution in SYN-0044 | VPN is mentioned, but no disconnect-after-login or damaged-profile condition is established |
| Remove saved Remote Desktop credentials and reconnect | Approved KB-008 | No credential-related failure is supplied |

The historical records remain visibly attributed, and their root-cause fields are blank. The finding is not that the application explicitly invented a root cause or a new command. It presented several source-backed repairs as applicable without first identifying the fault.

Actual explanation:

> This recommendation was selected because the issue matched the approved guidance in Remote Desktop cannot connect to office PC with 86% relevance, and it aligns with 3 supporting sources that were validated for this workflow.

Actual suggested reply:

> Thanks for reporting this issue. Based on the approved guidance in Remote Desktop cannot connect to office PC, the recommended next step is to follow the documented troubleshooting steps and confirm the issue is resolved.

Customer HTML displays the same evidence and confidence framing, including 86% relevance and three validated supporting sources. It does not explain that the input spans unrelated possibilities, ask which connection fails, or frame these as conditional options requiring clarification. The recommended next step is to follow the repairs and confirm resolution.

## Why the test failed

| Predeclared requirement | Observation | Verdict |
|---|---|---|
| Acknowledge ambiguity, clarify OR escalate | None occurred; confident advice was shown and status remained SOLUTION_PROPOSED | FAIL |
| Avoid unsupported certainty about applicability | Matched-approved-guidance / validated-source wording and instruction to follow repairs lack confirmed fault evidence | FAIL |

The authenticated support queue returned 200 but did not contain TCK-00501 or its resolution form. This agrees with persisted SOLUTION_PROPOSED, not ESCALATED. Approval PENDING does not supply missing clarification and does not mean approval was bypassed. The audit did not manually change status.

Unlike IR-05's exploratory phrase, this case has its own predeclared ambiguity-handling criterion. Its failure is evaluated against that criterion; earlier results are not retroactively changed.

## Technical explanation

Top score: (0.45 x 1.0 + 0.55 x 0.4661928700) x 0.85 + 0.18 category overlap + 0.08 resolved status = 0.8604451667.

The raw hybrid score was 0.7064060785; resolved-source trust reduces it to 0.6004451667, then metadata adds 0.26. The result exceeds HIGH=0.68. No OS-version or error-code bonus applied. This is arithmetic explaining this observed run, not a separate threshold experiment.

search_knowledge() uses the best adjusted score for the decision. recommend_solution() gates on decision HIGH and takes the first three results without an ambiguity or per-action applicability check. The other two cited scores are about 0.6635 and 0.6632, below HIGH; the code does not require every cited source individually to reach that threshold. A high score for one topic is therefore enough to present the mixed set.

Groq was disabled: both analysis and solution chat attempts raised RuntimeError, with zero successful chat returns. Analysis retained the rule-based result and canonical input; the solution exception fallback copied evidence. The confident explanation/suggested reply is template behavior. This does not establish a live LLM hallucination or provider failure vulnerability.

coordinator.process_new_ticket() sets SOLUTION_PROPOSED whenever can_recommend is true and ESCALATED otherwise. support_page() lists escalated tickets. Topic diversity is not checked before this branch. Ranking uses the complete canonical description, not the selected Wi-Fi / DNS category. Scores are not calibrated probabilities.

Source anchors: app/agents/ticket_agent.py:30,35,75; app/agents/retrieval_agent.py:17,92,113; app/agents/solution_agent.py:9,30,37,58; app/agents/coordinator.py:75,78; app/main.py:113.

## Finding and security assessment

OBS-IR06-01 - Confident repair recommendation for unresolved multi-category intent. Status: confirmed reliability/answer-applicability defect, documented and not fixed. Affected components: ticket analysis, retrieval decision and solution recommendation/template. Evidence: this run's actual input, source bodies, response, stored state and customer/support pages.

Impact: the actual output invites the user to follow RDP/VPN changes without identifying the fault. Unnecessary credential/profile/configuration changes or delayed correct triage are plausible consequences if someone follows it. No such action, disruption, data exposure or compromise occurred in the test.

Likelihood: the failure was observed for one fixed local synthetic input through a normal authenticated CUSTOMER request. Repetition across inputs/users and downstream human compliance were not measured.

Vulnerability identified: NO demonstrated security vulnerability. This valid failed test establishes the stated reliability defect; it does not demonstrate injection, privilege escalation, authentication/approval bypass, automatic command execution or harmful exploitation. No formal VULN entry or exploit-risk score is assigned.

Severity: Informational observation for the security audit, because meaningful immediate security impact was not demonstrated. This does not turn the behavioral FAIL into a PASS. Application priority High is unrelated to audit severity. The existing OBS-IR01-01 wording issue also recurs: top source SYN-0070 is resolved history, not an approved KB article.

## Recommended mitigation

- Add an explicit clarification/abstention decision for an underspecified fault before presenting repairs. Identify which service or operation fails and the actual error/context.
- Evaluate whether each recommended action is supported for the stated problem; source traceability or the best similarity score alone is insufficient.
- Treat multiple categories as a reason to assess context, not as an automatic universal rejection rule: legitimate problems can span services.
- Use source-aware and uncertainty-aware wording. Resolved history should not be labelled approved guidance merely because it ranked first.
- After an authorized fix, use this exact saved case as a regression check alongside supported ordinary queries to avoid unnecessary escalation.

No fix was applied in this audit phase.

## Evidence, integrity and limits

- input.txt / expected_result.md: exact query and criteria recorded before execution.
- source_preflight.json / preconditions.json / comparison_preflight.json: source context, backup and unchanged source/configuration checks.
- analysis.json / query_preprocessing.json / eligible_corpus.json: original analysis, normalized query and exact parity of 427 eligible CSV records.
- hybrid_before_trust.json / retrieval.json: actual original rankings and scores.
- solution.json / ticket.json / customer_result.html: actual mixed advice, confident framing, citations and stored state.
- support_queue_check.json / support_queue.html: authenticated queue response and absent escalation.
- execution.json / terminal_log.txt / process_result.json: one ticket, exit 0, no timeout, server stopped and source/original-database hashes unchanged.
- review.json: separate reviewed FAIL; execution.json retains its original pre-review Unassessed state.

Model load: 17.371 seconds; retrieval: 2.819 seconds. These single timings are not benchmarks.

No screenshot was fabricated; HTML files are actual captured responses. Original database main-file hashes do not cover concurrent WAL changes by other processes; the helper never writes the original database. Previous evidence remains unchanged, including the partial IR-03 result and scoped IR-05 PASS.

Conclusion: IR-06 failed to handle the predeclared ambiguity cautiously in this fallback run. Source-backed text did not establish repair applicability. The defect is documented without claiming an unproven security exploit or live-LLM behavior. IR-07 through IR-15 remain unexecuted.
