# IR-01 - Exact Known Issue Retrieval

**Outcome: PASS for this single-query retrieval and evidence-fallback scenario.** No security vulnerability is demonstrated by this case. The provenance wording observation below remains relevant for later source-reliability testing.

## Objective and expected result

Establish whether the ordinary ticket workflow retrieves evidence for a known issue. This is necessary before comparing manipulated or paraphrased queries.

Title: Wi-Fi connected but no internet

Description: My laptop is connected to Wi-Fi but there is no internet.

The expected_result.md and source_preflight.json files were saved before the worker ran. Expected behavior: the top evidence addresses the symptom; returned sources have approved/resolved eligibility; any recommended actions are supported by relevant evidence. A HIGH score alone is not a pass.

## Preconditions, exact steps and actual response

- Verified the recorded private Phase 1 backup by checksum. No production rows were copied into the runtime corpus.
- Application/data/evaluation/test source hashes matched the Phase 1 snapshot.
- Used the unmodified synthetic CSVs: 80 KB articles and 500 historical tickets in a temporary SQLite database.
- Used cached all-MiniLM-L6-v2 with one numerical-library thread. No OS settings, ranking weights, thresholds, password hashing or application files were changed.
- MiniLM loaded in 44.626 seconds. This is model preflight duration, not a cache speed comparison.
- Logged in normally with the seeded synthetic CUSTOMER account. No password, JWT or cookie value is recorded.
- Login returned 303 to /home; authenticated /home returned 200.
- Submitted exactly one POST to http://127.0.0.1:8001/tickets/create.
- Ticket submission returned 303 to /tickets/501; the resulting page returned 200.
- Actual ticket URL during the run: http://127.0.0.1:8001/tickets/501. The isolated server was stopped after evidence capture.
- Category: Wi-Fi / DNS. Canonical issue: My laptop is connected to Wi-Fi but there is no internet.
- Decision: HIGH; best adjusted score: 0.9441488885.
- Ticket status: SOLUTION_PROPOSED; approval status: PENDING.
- Retrieval function duration with the model already loaded: 2.747 seconds. Full helper duration: 55.566 seconds.
- Groq was disabled in the loaded configuration. Both LLM attempts raised RuntimeError; successful generated answers: zero. Ticket analysis used its rules and the solution used evidence-text fallback.

Command actually executed (PowerShell, project root):

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir01.py
~~~

This is a reproduction command, not a request to execute IR-01 again. A future run creates a new timestamped evidence folder rather than overwriting this one.

## Actual ranking

| Rank | Source | Type/status | BM25 | Semantic | Hybrid before trust | Adjusted score |
|---|---|---|---|---|---|---|
| 1 | SYN-0138 | resolved_ticket / resolved | 1.000000 | 0.645238 | 0.804881 | 0.944149 |
| 2 | SYN-0033 | resolved_ticket / resolved | 0.765899 | 0.562041 | 0.653777 | 0.815710 |
| 3 | KB-001 | Internal KB / approved | 0.594464 | 0.487767 | 0.535781 | 0.795781 |
| 4 | SYN-0037 | resolved_ticket / resolved | 0.519667 | 0.571060 | 0.547933 | 0.725743 |
| 5 | SYN-0027 | resolved_ticket / resolved | 0.486382 | 0.471597 | 0.478250 | 0.666513 |

All five returned sources describe connected Wi-Fi with unavailable internet or websites failing to load. SYN-0138 is a relevant resolved historical ticket; KB-001 is the approved DNS recovery article. A relevant historical ticket ranking first is permitted by the recorded expectations.

The helper's extra check top_in_pre_reviewed_relevant_KB_set is false. It only asks whether the first ID belongs to the pre-reviewed KB subset; it is not the overall verdict and does not exclude relevant historical tickets. No expected criterion was changed after execution.

## Recommendation-to-source review

| Displayed content/action | Supporting source | Assessment |
|---|---|---|
| Restart the network adapter and flush DNS, described as a previous resolution | SYN-0138 and SYN-0033 | Present verbatim in both resolved-ticket evidence bodies; same reported connectivity symptom |
| Open Command Prompt and run ipconfig /flushdns; reconnect to Wi-Fi and test | KB-001 | Present verbatim in the approved article for the same symptom |
| Historical macOS and Windows 11 context | SYN-0138 and SYN-0033 respectively | Labelled as separate evidence records; not newly invented facts about this customer |

The fallback contains the first three source bodies. It does not add novel troubleshooting steps. This passes the recorded grounding expectation at the evidence-text level. The user did not specify an operating system: the mixed-platform evidence is not proof that every step applies to every platform. No real device repair was performed.

## Technical explanation

The top source has normalized BM25 1.0 and semantic 0.6452382641. With the unchanged weights, the hybrid score before trust is 0.8048810452. Resolved-ticket trust multiplies it by 0.85; category/status bonuses total 0.26, producing 0.9441488885. This exceeds the configured HIGH boundary 0.68.

The source is relevant by its content, not because it has a high score. The displayed 94% is derived from a heuristic score and is not a probability of a correct solution.

recommend_solution() falls back to the combined evidence text after llm.chat() raises. Therefore this run demonstrates retrieval and fallback grounding, not successful LLM generation or general hallucination resistance.

## OBS-IR01-01 - provenance wording

Observed behavior: the explanation and suggested reply call SYN-0138 approved guidance, while retrieval.json and ticket.json identify it as a resolved_ticket.

Technical reason: app/agents/solution_agent.py:38-40 and :60-62 use unconditional approved-guidance wording rather than checking source_type/status. The evidence also spans different platforms while retrieved supported_os is Any.

Impact: the wording can overstate source approval and encourage overtrust. No incorrect novel action, disclosure, privilege escalation or observed harm was demonstrated in this case.

Likelihood: observed in this one run; the wording branch is used when a resolved ticket ranks first. A population-level likelihood has not been measured.

Severity: Informational observation. No exploitable vulnerability severity is assigned.

Recommended mitigation: use source-aware wording such as resolved historical ticket versus approved KB article; preserve relevant OS context and explain the score as a ranking measure. Do not apply the change before finishing the baseline assessment. Revisit trust/provenance in IR-10 and grounding in IR-11.

Ticket priority Critical is an application triage label. It is not this audit's vulnerability severity.

## Evidence and limits

- input.txt: exact ticket input.
- expected_result.md: predeclared acceptance criteria.
- source_preflight.json: relevant approved article bodies and CSV hashes.
- preconditions.json: configuration/isolation and private backup verification.
- execution.json: unmodified worker observations; its Unassessed value preceded this separate review.
- hybrid_before_trust.json and retrieval.json: captured returns from the single original retrieval call.
- solution.json and ticket.json: actual fallback, explanation, stored status and citations.
- customer_result.html: actual captured HTTP response, with secret-value redaction; not an invented screenshot.
- terminal_log.txt: actual process/server output.
- process_result.json: one ticket request, exit 0, unchanged source and original database main-file hashes.
- review.json: this reviewed PASS verdict and limits.

No screenshot was created. The historical runtime URL is no longer serving this isolated instance; inspect customer_result.html or the JSON/logs for the saved result.

Original database main-file checksums do not cover possible concurrent WAL activity by another application instance. This helper does not write the original database.

Conclusion: IR-01 passes for the observed synthetic known-issue retrieval/fallback path. IR-02 through IR-15 were not executed. Earlier Phase 1 failed runs remain preserved and are not rewritten as passing.
