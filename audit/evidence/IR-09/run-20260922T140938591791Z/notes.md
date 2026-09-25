# IR-09 - Draft / Unapproved KB Exclusion

**Outcome: PASS for draft exclusion and the approved control on the tested ticket workflow.** The draft was absent from the complete eligible corpus before ranking and from all ranked/cited/recommended evidence in both runs. The control remained eligible and was retrieved and cited for its own marker. A separate unrelated-VPN recommendation defect was observed in the control answer and is documented below.

## Objective and exact input

Verify that unreviewed draft knowledge is not treated as approved retrieval evidence. Use one harmless unique draft marker and a separate approved positive control.

| Subcase | Exact description | Length | Title |
|---|---|---:|---|
| draft_probe | `quartzmeadow729` | 15 | Audit reference lookup |
| approved_control | `cobaltlantern463` | 16 | Audit reference lookup |

Both markers exceed the route minimum and survive masking, canonicalization and normalization unchanged. Each was submitted exactly once, with both fixtures present in each fresh database. The paired queries use identical eligible records, settings and source code; they are not a matched-score or relative-authority experiment.

## Fixed fixtures and backups

| Field | Draft | Approved control |
|---|---|---|
| Source ID | AUDIT-IR09-DRAFT-001 | AUDIT-IR09-CONTROL-001 |
| Title | Draft lookup quartzmeadow729 | Approved lookup cobaltlantern463 |
| Status before / after | draft / draft | approved / approved |
| Source type | internal_kb | internal_kb |
| Authoritative flag | true | true |
| Category / OS | Audit / Lookup / Any | Audit / Lookup / Any |
| Response-only witness | violetcompassstamp | amberharborreceipt |

Both author fields are IR-09 synthetic audit fixture, security class internal, and creation/update metadata 2026-09-22. These are synthetic setup values, not proof of an approval workflow or validated support advice. The draft remains excluded despite its internal_kb type and authoritative flag. This is the tested configuration, not a broad metadata-attack matrix.

Draft body:

> Unreviewed reference for quartzmeadow729. Response-only witness: violetcompassstamp. This synthetic record is not approved for recommendations.

Approved body:

> Reviewed test reference for cobaltlantern463. Response-only witness: amberharborreceipt. This is harmless synthetic lookup text, not a device repair.

All four unique marker/witness strings were absent from the original CSVs before setup. The response-only witnesses were not submitted in either query. The two new records exist only in temporary synthetic databases. Original articles, CSVs, app behavior and working knowgap.db were not modified.

The existing private working-DB backup was verified. Each isolated database was also snapshotted with sqlite3.Connection.backup from a read-only source after seeding and before requests; PRAGMA integrity_check returned ok. Both snapshot files remain private outside the repository, with only metadata/hashes in evidence. All fixture fields/statuses and snapshot hashes were checked after execution and at review.

The documented backup command is `python -B audit/scripts/collect_baseline.py backup`. IR-09 independently creates its own before_requests.sqlite snapshots; it does not overwrite the earlier backup evidence.

## Criteria declared before requests

- PASS: draft absent from the entire actual eligible corpus, both ranking stages, selected source/citations and recommendation content; approved control remains eligible and is retrieved by its own query.
- FAIL: valid execution includes or recommends the draft as authoritative evidence, or excludes the approved control. A control retrieval miss with correct eligibility would be reported separately, not invented draft leakage.
- Inspect actual pre-ranking records; absence from top-k alone is insufficient. Pure trust=0 output is a separate check and does not prove exclusion.
- Distinguish legitimate query echo in description/history/UI from source leakage using the draft ID, response-only witness and content/attribution.
- Missing backup, model, login, fixture or query prerequisites would mean Not ready/Inconclusive. Preserve status throughout; no approving the draft or fixing code during the test.

## Preconditions and procedure

Each database held 82 articles (80 original approved articles plus one draft and one approved control), 500 historical tickets and active synthetic CUSTOMER/IT_SUPPORT accounts. The actual eligible corpus contained 81 approved articles and 347 resolved tickets: 428 records. No original working-database rows were copied.

Both full eligible-corpus hashes: `02ffde5f1a50e2e6e28eeb956dedaf74511ddad40f3826689552c63f43ba3806`. The saved seven-field records exactly match the original CSV-derived approved/resolved records plus the control, with the draft excluded.

Settings matched earlier cases: all-MiniLM-L6-v2 cached model, BM25/semantic 0.45/0.55, HIGH=0.68, UNCERTAIN=0.55, top-k=5 and one numerical-library thread. Groq model setting llama-3.1-8b-instant; Groq disabled.

1. Saved exact markers, fixtures, uniqueness check and expected_result.md before requests.
2. Loaded the cached model, verified database isolation, seeded both fixtures and the original synthetic corpus, checked statuses and created a private consistent snapshot.
3. Started an owned loopback server and logged in normally as CUSTOMER.
4. Submitted the subcase once; observed original analysis, full eligible corpus, preprocessing, rankings, trust calls and solution results without changing arguments/results.
5. Saved ticket/citations and actual customer HTML; logged in as IT_SUPPORT and read the queue.
6. Verified unchanged fixture fields and backups, stopped each server and compared application/source/main-database hashes. No approval, resolution, manual escalation or repair was performed.

Reproduction command (already run; a rerun creates new evidence and temporary databases):

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir09.py
~~~

Both sequential local servers used POST http://127.0.0.1:8001/tickets/create and GET /tickets/501. Each TCK-00501 belongs to its own isolated DB. Health 200, CUSTOMER login 303 to /home, home 200, creation 303, ticket page 200, IT_SUPPORT login 303 and support page 200 in both runs. Both servers stopped. Passwords, cookies and access tokens are not recorded.

## Results

| Check | Draft-marker query | Approved-control query |
|---|---|---|
| Marker preserved into retrieval | Yes | Yes |
| Draft in full corpus / rankings / citations | Absent / absent / absent | Absent / absent / absent |
| Draft witness in recommendation or customer HTML | Absent | Absent |
| Approved control eligible / rank | Yes / 1 | Yes / 1 |
| Best score / decision | 0.2510261122 / LOW | 0.8533253620 / HIGH |
| Citation count | 0 | 3 |
| Stored state / approval | ESCALATED / PENDING | SOLUTION_PROPOSED / PENDING |
| Support queue | Present | Absent |
| Draft status after query | draft | draft |
| Primary outcome | PASS | PASS |

The control can appear as a weak semantic candidate for the unrelated draft marker without revealing draft content. Its draft-query BM25 score is zero, and the LOW result suppresses recommendations/citations. The query marker appears in the customer description/history, as expected; its absence is not the confidentiality criterion. The unsubmitted draft witness and draft ID are absent from the page and answer.

## Complete ranked results

### draft_probe

| Rank | Source | Status | BM25 | Semantic | Raw hybrid | Final score | Cited |
|---|---|---|---:|---:|---:|---:|---|
| 1 | AUDIT-IR09-CONTROL-001 | approved | 0.000000 | 0.310957 | 0.171026 | 0.2510261122 | No |
| 2 | SYN-0003 | resolved | 0.000000 | 0.131175 | 0.072146 | 0.1413244893 | No |
| 3 | KB-007 | approved | 0.000000 | 0.109754 | 0.060365 | 0.1403649328 | No |
| 4 | SYN-0059 | resolved | 0.000000 | 0.117744 | 0.064759 | 0.1350455093 | No |
| 5 | SYN-0011 | resolved | 0.000000 | 0.108323 | 0.059578 | 0.1306409082 | No |

Actual final message:

~~~text
No sufficiently reliable solution was found in the available knowledge base or previous resolved tickets. The ticket has been escalated to IT Support.
~~~

Actual explanation:

> No approved knowledge article met the reliability threshold for this issue. The search score was too weak or the evidence was incomplete, so a human specialist should review it.

Actual suggested reply:

> Thanks for reporting this. I have escalated the request to a specialist because the available evidence was not strong enough to provide a safe automated recommendation.

### approved_control

| Rank | Source | Status | BM25 | Semantic | Raw hybrid | Final score | Cited |
|---|---|---|---:|---:|---:|---:|---|
| 1 | AUDIT-IR09-CONTROL-001 | approved | 1.000000 | 0.587864 | 0.773325 | 0.8533253620 | Yes |
| 2 | SYN-0001 | resolved | 0.000000 | 0.183299 | 0.100814 | 0.1656920711 | Yes |
| 3 | KB-002 | approved | 0.000000 | 0.155633 | 0.085598 | 0.1655982335 | Yes |
| 4 | KB-008 | approved | 0.000000 | 0.152249 | 0.083737 | 0.1637368470 | No |
| 5 | SYN-0048 | resolved | 0.000000 | 0.175459 | 0.096502 | 0.1620270152 | No |

Actual final message:

~~~text
Evidence source AUDIT-IR09-CONTROL-001 | Approved lookup cobaltlantern463
Reviewed test reference for cobaltlantern463. Response-only witness: amberharborreceipt. This is harmless synthetic lookup text, not a device repair.

Evidence source SYN-0001 | VPN disconnects every few minutes
Problem: VPN disconnects every few minutes on Windows 11. I already restarted the device once.
Root cause: 
Resolution: Updated the VPN client and re-created the connection profile.

Evidence source KB-002 | Re-create VPN Profile - Guide 1
Remove the damaged VPN connection profile and create a new profile using the approved organization settings.
~~~

Actual explanation:

> This recommendation was selected because the issue matched the approved guidance in Approved lookup cobaltlantern463 with 85% relevance, and it aligns with 3 supporting sources that were validated for this workflow.

Actual suggested reply:

> Thanks for reporting this issue. Based on the approved guidance in Approved lookup cobaltlantern463, the recommended next step is to follow the documented troubleshooting steps and confirm the issue is resolved.

## Exclusion mechanism and trust diagnostics

`_records_from_db()` selects KnowledgeArticle.status == approved before constructing the records sent to hybrid_rank (`app/agents/retrieval_agent.py:56-71`). Only RESOLVED tickets with resolution notes are added. The actual full corpus capture establishes exclusion before deduplication, BM25, embeddings and top-k. The draft did not merely receive a low rank.

`_trust_weight()` checks draft status before the internal_kb rule (`app/agents/retrieval_agent.py:43-52`). Direct calls to the original helper on the declared fixture records returned draft=0.0 and control=1.0; these are labelled pure diagnostics. Actual search trust calls included the control at 1.0 and never included the draft. Therefore the runtime exclusion conclusion rests on the database filter and actual corpus evidence, not on executing a draft-weight branch during ranking.

`search_knowledge()` multiplies the hybrid score by trust and then adds metadata (`:101`). A zero trust multiplier alone is not a guarantee that an arbitrary supplied record cannot receive a metadata bonus. No alternate direct-ranker path was tested here; the observed ticket path excludes the draft earlier.

For the control marker, `(0.45*1 + 0.55*0.5878642946)*1 + 0.08 = 0.8533253620`. For the draft marker, the weak control candidate receives `(0.45*0 + 0.55*0.3109565676)*1 + 0.08 = 0.2510261122`. Category/OS bonuses and exact-code boosts do not explain either control score. These are descriptive values, not probabilities or an IR-10 trust comparison.

The LOW draft probe triggers recommend_solution() template escalation, so no source is proposed and no citations are stored. The ticket is visible in the normal authenticated support queue, still unassigned. Queue visibility is not human acknowledgment or completed assistance.

## Separate quality observation: unrelated secondary advice

**OBS-IR09-01:** the approved control is correctly retrieved, but its HIGH best score causes recommend_solution() to include the first three results. SYN-0001 (0.1656920711) and KB-002 (0.1655982335) are unrelated VPN sources; each has BM25=0 and a score far below UNCERTAIN 0.55. The marker query describes no VPN fault. Their VPN profile/update guidance nevertheless appears verbatim in the answer, and the template calls all three sources validated and tells the user to follow troubleshooting steps.

This is a confirmed relevance/applicability defect in this synthetic control response, consistent with earlier first-three-source observations. The fallback text is copied from eligible approved/resolved sources, not invented or leaked from the draft. The control body explicitly says it is not a device repair. The source-status exclusion PASS does not certify the relevance or safety of all recommended actions.

Impact: unnecessary VPN profile changes or delayed triage would be possible if the advice were followed, but no action or real harm occurred. Likelihood: observed once with this control marker; general prevalence is unmeasured. Severity: Informational on the demonstrated security-impact scale; no exploit-risk score or formal VULN entry. Suggested mitigation: after approval, validate each cited action against the actual request, avoid copying irrelevant low-score results simply to fill three slots, and use accurate source/uncertainty wording. No application fix applied.

## Security assessment, limits and conclusion

- Vulnerability identified: NO demonstrated unapproved-source use, approval bypass, data exposure or security exploit. The primary source-status boundary held in both cases.
- Primary impact/severity: no adverse exclusion failure observed; no vulnerability severity assigned. The separate answer-quality defect remains documented above.
- Likelihood/generalization: two queries, one fixed draft/control fixture pair and one normal ticket route. No production prevalence or universal exclusion claim.
- Groq limitation: configured disabled; draft probe has one failed analysis attempt and no solution-generation attempt, control has two failed attempts. Zero successful provider returns. Results apply to rule/template/evidence fallback.
- Scope limitation: statuses were set in isolated setup, not through an approval route. No malicious status mutation, alternate API/direct-ranker caller, every non-approved status, live generated answer or IR-10 authority comparison was tested.
- Data/environment: small synthetic dataset, local servers, no real user data, no actual human response or device repair. Private snapshots stay outside the repository.
- Recommended retention: preserve the approved-only database filter and keep regression coverage for draft/control exclusion when implementation changes. The direct helper result does not replace corpus-level evidence.

## Evidence index

| Files | Evidence |
|---|---|
| inputs.json / fixtures.json / expected_result.md | Exact predeclared queries, fixtures and PASS/FAIL rules |
| source_preflight.json / preconditions.json / comparison_preflight.json | Marker uniqueness, source hashes, working-DB backup and settings assumptions |
| Each subcase: fixture_preflight.json / isolated_database_backup.json / fixture_postflight.json | Stored status/content before/after and private consistent snapshots |
| Each subcase: analysis.json / query_preprocessing.json | Actual marker survival through input processing |
| Each subcase: eligible_records.json / eligible_corpus.json | Complete observed pre-ranking corpus and equality checks |
| Each subcase: trust_preflight.json / actual_trust_calls.json | Pure helper diagnostics separately from runtime trust calls |
| Each subcase: hybrid_before_trust.json / retrieval.json / solution.json / ticket.json / leakage_checks.json | Rankings, decisions, full answers, citations and draft-leakage checks |
| Each subcase: customer_result.html / support_queue.html / support_queue_check.json | Actual HTTP responses and normal support-queue observation |
| Each subcase: execution.json / terminal_log.txt / process_result.json | One request, timings, LLM mode, server stop and integrity |
| comparison.json / comparison.csv / review.json / notes.md | Separate derived comparison and reviewed verdict |

HTML files are actual saved responses, not screenshots. Raw worker status remains awaiting review; review.json provides the later verdict. All prior evidence and raw current captures remain unchanged. Application/data/evaluation/test and working-database main-file hashes match baseline; main-file hashes do not cover unrelated concurrent WAL writes. The helper never writes the working database.

**Conclusion:** IR-09 passes draft exclusion and approved-control availability for this ticket path. A separate secondary-source recommendation defect is recorded without claiming a draft leak or security exploit. IR-10 through IR-15 remain unexecuted; stop before IR-10.
