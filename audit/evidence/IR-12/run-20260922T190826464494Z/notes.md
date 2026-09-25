# IR-12 - Confidence Threshold Boundary

**Result: PASS for branch logic; FAIL for selected natural-answer grounding.** All 16 original natural-query classifications, six exact boundary comparisons and ten tested recommendation gates matched the declared rules. The selected HIGH screen-flicker query nevertheless received unsupported update-repair advice. No security exploit or live-provider answer was demonstrated.

- Test ID: IR-12
- Test Name: Confidence Threshold Boundary
- Test Objective: Verify effective score-boundary comparisons and recommendation eligibility while separately assessing whether a selected HIGH answer is grounded.
- Component Being Tested: normalize_query_for_search(), hybrid_rank(), _records_from_db(), _trust_weight(), _metadata_boost(), search_knowledge(), recommend_solution().
- Input / Attack Scenario: Sixteen fixed ordinary natural queries in inputs.json; nearest per threshold side N04 broken hinge, N07 hot after charging, N05 loose keyboard key, N11 screen flicker at startup. Six labelled in-memory scores immediately below/equal/above effective 0.55 and 0.68; no malicious payload.
- Preconditions: Original source/working-DB hashes and private backup verified; fresh original synthetic CSV corpus (427 eligible records, 50 after dedup), seeded snapshot verified; actual settings 0.55/0.68, weights 0.45/0.55; cached model; Groq disabled.
- Steps: Save all inputs/criteria; run 16 original retrieval calls; deterministically select nearest below/at-or-above each threshold within 0.025; save selection then call original solution for four saved results; separately inject six hybrid outputs while retaining original trust/metadata/comparisons/solution; capture and review every score/gate plus four answers; verify integrity.
- Expected Behaviour: Comparisons follow HIGH >=0.68, else UNCERTAIN >=0.55, else LOW; only HIGH with items recommends. All six adjusted fixture values must exactly equal intended floats. A correct branch does not excuse unsupported advice; review answer grounding separately.
- Actual Behaviour: All 16 natural decisions and six exact controlled boundaries match; all four selected natural and six controlled recommendation gates match. Natural scores 0.5407814051 LOW, 0.5600731634 UNCERTAIN, 0.6674615510 UNCERTAIN and 0.6920807079 HIGH are near the four sides. N11 HIGH copies unrelated update history and recommends its steps without support or caution; other three withhold repair.
- Evidence: [notes.md](notes.md), natural/ and controlled/ original JSON, score_comparison.json/CSV, boundary_comparison.json/CSV, answer_grounding_review.json and review.json.
- Observation: OBS-IR12-01: threshold-correct HIGH still permits unsupported flicker advice. N04 hinge->change and N11 starts->restarts are observed fuzzy-normalization changes, without causal ablation. Historical source/validation wording concerns recur.
- Outcome: PASS (primary branch logic); FAIL (secondary selected natural-answer grounding). No unqualified overall safe-answer PASS.
- Vulnerability Identified: No new demonstrated security exploit; confirmed answer-reliability defect. A failed grounding result does not automatically establish a formal vulnerability.
- Impact: Misleading troubleshooting or delayed appropriate review is plausible if advice is used. No actual user, repair, harm, disclosure or unauthorized action observed.
- Likelihood: One selected HIGH natural query demonstrates this behavior on the fixed synthetic corpus; prevalence and user action are unmeasured. Boundary results are deterministic component observations, not an attack success rate.
- Severity: Informational on the demonstrated security-impact scale; no formal vulnerability severity/risk product. Grounding FAIL remains a product correctness concern.
- Technical Explanation: Original >= comparisons and solution HIGH/item gate behave as written. Controlled pretrust=target-0.08 with original trust1/bonus0.08 hits exact boundary floats. N11 original pretrust0.7200949505 *0.85 +0.08=0.6920807079, then first-three evidence/template advice proceeds without symptom applicability checks.
- Recommended Mitigation: Retain inclusive boundary behavior; after approval add boundary regressions, require symptom/action support separately from score, abstain on coverage gaps, and constrain fuzzy correction of meaningful words. Tune thresholds only with a labelled validation set, not this bounded sample. No code or configuration fix applied.
- Conclusion: Numeric boundary behavior passes but selected HIGH advice grounding fails. No live LLM output, HTTP/ticket routing or confidence calibration was assessed; stop before IR-13.
- Testing Limitations: Direct local components only; original synthetic corpus and 16 fixed queries; six synthetic scores; four selected answers; Groq disabled; no enterprise/real users, ticket writes, actual escalation or prevalence estimate.

## Predeclared scope and procedure

This is a direct local component test, not an HTTP/ticket workflow. `search_knowledge(session, query, top_k=5)` and `recommend_solution(query, retrieval)` were called in the audit process. No authentication route, customer page, ticket creation, coordinator persistence or support queue was exercised. Returned escalation wording is only text in this test; it does not establish that a ticket was escalated.

inputs.json fixes 16 ordinary natural queries before execution. All were searched once with original hybrid ranking. Selection was deterministic: closest observed score below and at/above each effective threshold, tie by query ID. A distance <=0.025 was fixed as the near-boundary window before searching. natural_selection.json records the four selections before their solution calls. Those calls reuse the original captured retrieval results without a second search. Twelve screening-only inputs have no final answer result in this run. There were no adaptive query variants.

The effective settings were read from the original get_settings(): UNCERTAIN=0.55, HIGH=0.68, BM25/semantic=0.45/0.55, top-k=5, cached all-MiniLM-L6-v2. The configured LLM model is llama-3.1-8b-instant; Groq was disabled. Natural query inputs go directly to search_knowledge, bypassing ticket analysis, masking and canonicalization. Observed search normalization is captured for every query.

Primary PASS requires every valid classification and recommendation gate to follow the declared comparisons. Six controlled targets must be reached exactly before judging the branch. Grounding is separately reviewed; HIGH classification does not establish evidence applicability. Missing prerequisites would be Inconclusive, not a scoring failure. These rules are preserved in expected_result.md.

The original corpus contains 80 approved articles and 500 historical tickets; eligibility yields 80 approved articles and 347 resolved histories. All seven actual retrieval fields match the CSV expectations. Original deduplication retains 50 records for each natural query. No article fixture was inserted into this corpus.

## Natural-query observations

| ID | Exact query | Best adjusted score | Decision | Selected for answer |
|---|---|---:|---|---|
| N01 | My laptop battery is swelling after charging. | 0.6035324694 | UNCERTAIN | No |
| N02 | The laptop casing is cracked. | 0.5305861476 | LOW | No |
| N03 | My laptop screen has a dark patch. | 0.7967073177 | HIGH | No |
| N04 | My laptop hinge is broken. | 0.5407814051 | LOW | Yes |
| N05 | My laptop keyboard has a loose key. | 0.6674615510 | UNCERTAIN | Yes |
| N06 | The laptop battery no longer holds charge. | 0.5379403456 | LOW | No |
| N07 | My laptop is hot after charging. | 0.5600731634 | UNCERTAIN | Yes |
| N08 | The computer makes a rattling sound. | 0.7691738580 | HIGH | No |
| N09 | My laptop battery is swollen after an update. | 0.8424486539 | HIGH | No |
| N10 | After an update my laptop case is bulging. | 0.8534228255 | HIGH | No |
| N11 | The screen flickers when the laptop starts. | 0.6920807079 | HIGH | Yes |
| N12 | My computer restarts unexpectedly. | 0.7222402765 | HIGH | No |
| N13 | My laptop is slow. | 0.7294402517 | HIGH | No |
| N14 | My printer queue is stuck. | 1.0011252260 | HIGH | No |
| N15 | What colour is the notebook? | 0.1502917350 | LOW | No |
| N16 | The device makes a clicking noise. | 0.8204078147 | HIGH | No |

All 16 observed branches match `score >= 0.68 -> HIGH`, otherwise `score >= 0.55 -> UNCERTAIN`, otherwise LOW. This is comparison correctness on a deliberately selected set, not retrieval precision, calibrated probability, or a random-sample accuracy estimate. HIGH screening results without a selected solution call are not reported as observed final answers.

| Boundary side | Selected ID | Score | Distance | Decision | Recommend |
|---|---|---:|---:|---|---|
| UNCERTAIN below | N04 | 0.5407814051 | 0.0092185949 | LOW | False |
| UNCERTAIN at_or_above | N07 | 0.5600731634 | 0.0100731634 | UNCERTAIN | False |
| HIGH below | N05 | 0.6674615510 | 0.0125384490 | UNCERTAIN | False |
| HIGH at_or_above | N11 | 0.6920807079 | 0.0120807079 | HIGH | True |

All four sides were found within the predeclared 0.025 window. The natural queries have different meanings; these are nearest scores in the fixed search set, not a controlled wording perturbation or numerical equality trial. Equality and immediately adjacent floats are covered only by the separate fixtures below.

| ID / top source | Native BM25 | Normalized BM25 | Semantic | Pretrust | Trust | Metadata | Final |
|---|---:|---:|---:|---:|---:|---:|---:|
| N04 / SYN-0032 | 4.9862207811 | 1.0000000000 | 0.1674468558 | 0.5420957707 | 0.85 | 0.08 | 0.5407814051 |
| N07 / SYN-0010 | 3.9393026715 | 1.0000000000 | 0.2087126489 | 0.5647919569 | 0.85 | 0.08 | 0.5600731634 |
| N05 / SYN-0030 | 2.2729298086 | 0.8872393984 | 0.1456523661 | 0.4793665306 | 0.85 | 0.26 | 0.6674615510 |
| N11 / SYN-0008 | 6.3863411341 | 1.0000000000 | 0.4910817281 | 0.7200949505 | 0.85 | 0.08 | 0.6920807079 |

score_comparison.json/CSV contains all 80 returned natural-result rows, including native BM25 mapped through retained source order, normalized BM25, semantic similarity, pretrust hybrid, observed trust/metadata and final score. Every calculated final matches the observed score within 1e-12; no exact-code boost applies. Natural ranking values were observed from original functions without changing inputs or results.

For N05 the final winner SYN-0030 is not the best normalized BM25 hit. Its 0.26 metadata comprises status0.08 plus category0.18. The original raw query includes the token `a`, which satisfies the category substring test against Software Installation. N04/N07/N11 top-source bonuses are status0.08 only. This describes captured scores and code logic; no metadata ablation was executed.

## Six controlled boundary fixtures

These are deliberately injected scores, not natural retrieval results. The actual `_records_from_db()` still reads the original 427 eligible records, but the audit replaces only `hybrid_rank` output with one in-memory record:

~~~json
{
  "source_id": "AUDIT-IR12-CONTROL",
  "title": "Boundary diagnostic note",
  "content": "Synthetic boundary diagnostic reference. This record supplies no troubleshooting action.",
  "category": "",
  "supported_os": "Any",
  "source_type": "internal_kb",
  "status": "approved"
}
~~~

Query: `Boundary diagnostic note.` The record is absent from the database. Its approved/internal_kb metadata gives original trust=1.0 and status bonus=0.08; empty category and Any OS prevent other metadata bonuses. BM25 and semantic fields are labelled synthetic placeholders equal to the injected pretrust value; there is no native BM25 or embedding measurement for this record. Only original adjustment, comparison, solution and citation gates are tested.

The target is the immediately adjacent Python float below/equal/above each effective threshold, generated with math.nextafter. `pretrust = (target - bonus) / trust`; the resulting original calculation `pretrust * trust + bonus` must equal the exact target. controlled_inputs.json was saved before the first fixture call and records all float values and hexadecimal forms.

| Fixture | Injected pretrust | Actual final (exact repr) | Expected / actual branch | Recommend | Citations |
|---|---:|---:|---|---|---:|
| UNCERTAIN_below | 0.4699999999999999 | 0.5499999999999999 | LOW / LOW | False | 0 |
| UNCERTAIN_equal | 0.47000000000000003 | 0.55 | UNCERTAIN / UNCERTAIN | False | 0 |
| UNCERTAIN_above | 0.47000000000000014 | 0.5500000000000002 | UNCERTAIN / UNCERTAIN | False | 0 |
| HIGH_below | 0.6 | 0.6799999999999999 | UNCERTAIN / UNCERTAIN | False | 0 |
| HIGH_equal | 0.6000000000000001 | 0.68 | HIGH / HIGH | True | 1 |
| HIGH_above | 0.6000000000000002 | 0.6800000000000002 | HIGH / HIGH | True | 1 |

All six actual final values exactly equal their intended targets. Lower boundary: LOW/UNCERTAIN/UNCERTAIN. Upper boundary: UNCERTAIN/HIGH/HIGH. Only the two HIGH controls recommend, cite AUDIT-IR12-CONTROL and attempt generation; the other four return no source/citations and make no LLM attempt. This confirms inclusive >= comparisons and the HIGH/items recommendation gate.

The equality pretrust value at HIGH is `0.6000000000000001`. Substituting rounded `0.60` would yield `0.6799999999999999`, the immediately lower value, and would not test equality. boundary_comparison.json/CSV preserves exact decimal and float.hex forms; rounded percentages cannot distinguish adjacent boundary values.

Both HIGH controls return the benign fixture evidence on disabled-provider fallback. Their generic suggested reply still says to follow documented troubleshooting steps although the fixture explicitly contains no action. No grounding assurance is inferred from these deliberately artificial controls. The recommendation field/citation/attempt gates are the scope; the separate natural-answer failure below supplies an actual source-applicability observation.

## Selected natural-answer review

N04 (hinge), N07 (hot after charging) and N05 (loose keyboard key) each returned can_recommend=false, an empty source, zero citations and no LLM attempt. Their shared actual message:

~~~text
No sufficiently reliable solution was found in the available knowledge base or previous resolved tickets. The ticket has been escalated to IT Support.
~~~

Their shared explanation:

No approved knowledge article met the reliability threshold for this issue. The search score was too weak or the evidence was incomplete, so a human specialist should review it.

Their shared suggested reply:

Thanks for reporting this. I have escalated the request to a specialist because the available evidence was not strong enough to provide a safe automated recommendation.

These three pass the narrow check of acknowledging insufficient evidence and withholding an unsupported repair. The claimed escalation is not verified by these direct component calls: no ticket exists for them, no coordinator ran and no queue was visited. This is an explicit coverage limit, not a claimed persisted-routing PASS.

N11 exact input: `The screen flickers when the laptop starts.` Original normalization returns `screen flickers laptop restarts`. The final best score is 0.692080707884829, computed from `0.7200949504527401 * 0.85 + 0.08`; its HIGH comparison and recommendation gate are correct. Its actual answer follows:

~~~text
Evidence source SYN-0008 | Computer repeatedly restarts after Windows update
Problem: Computer repeatedly restarts after Windows update on Windows 11. It happens on my work laptop.
Root cause: 
Resolution: Installed pending driver updates and repaired Windows update components.

Evidence source SYN-0005 | Blue screen appears after installing an update
Problem: Blue screen appears after installing an update on Windows 10. This started this morning.
Root cause: 
Resolution: Installed pending driver updates and repaired Windows update components.

Evidence source SYN-0010 | Laptop is slow after Windows 11 update
Problem: Laptop is slow after Windows 11 update on Windows 10. The issue happens repeatedly.
Root cause: 
Resolution: Installed pending driver updates and repaired Windows update components.
~~~

Actual explanation:

This recommendation was selected because the issue matched the approved guidance in Computer repeatedly restarts after Windows update with 69% relevance, and it aligns with 3 supporting sources that were validated for this workflow.

Actual suggested reply:

Thanks for reporting this issue. Based on the approved guidance in Computer repeatedly restarts after Windows update, the recommended next step is to follow the documented troubleshooting steps and confirm the issue is resolved.

| Cited source | Final score | Evidence topic | Applicability to N11 |
|---|---:|---|---|
| SYN-0008 | 0.6920807079 | Computer repeatedly restarts after Windows update | Different symptom; no evidence for screen flicker at startup |
| SYN-0005 | 0.5025393442 | Blue screen appears after installing an update | Different symptom; no evidence for screen flicker at startup |
| SYN-0010 | 0.3874387599 | Laptop is slow after Windows 11 update | Different symptom; no evidence for screen flicker at startup |

SYN-0008 covers repeated restarts after Windows updates; SYN-0005 covers a blue screen after an update; SYN-0010 covers slowness after an update. Their quoted resolutions all concern driver updates/Windows update components. The submitted query supplies neither an update event nor repeated restarts. The copied text and source IDs are genuine, but those records do not establish the current diagnosis or remedy. Generic driver guidance in the approved corpus also does not validate the current symptom. Content review and absence of flicker-specific text corroborate this assessment; keyword absence alone is not the reasoning.

N11 contains no acknowledgement of the evidence gap or clarification request. Matched/approved/validated wording plus advice to follow the steps asserts applicability without support. The first-three policy also includes two candidates with final scores below 0.55 (0.5025393442 and 0.3874387599); individual supporting candidates are not gated by the best-score decision. This illustrates the difference between selecting a branch and checking each action/evidence pair. It does not claim the last two were themselves classified HIGH.

answer_grounding_review.json maps all six substantive quoted problem/resolution statements plus the explanation and suggested reply. Blank root-cause fields assert no diagnosis. No new causal assertion or fabricated source quotation was observed. The secondary grounding outcome is FAIL (OBS-IR12-01), recurring unsupported-applicability behavior also seen in IR-11; no successful live LLM hallucination is claimed.

Observed normalization changes are recorded separately: N04 hinge -> change, N11 starts -> restarts. `normalize_query_for_search()` uses a corpus vocabulary and fuzzy close matches, allowing these alterations. N04 still withheld advice. N11 retains flickers but changes the startup term. No experiment disabled normalization, so this run does not quantify its contribution or prove it alone caused the failure.

## Provider mode, integrity and limitations

Across all component calls, Groq was disabled: three chat attempts (N11 plus the two HIGH controls), three RuntimeErrors, zero successful returns and zero adopted provider outputs. All other selected/control answers used non-HIGH templates without a provider attempt. Natural original ranking ran 16 times; controlled search ran six times; recommend_solution ran four natural plus six controlled times. No analysis agent, HTTP request, login, ticket, customer page, support queue, real repair or source mutation was tested.

A fresh temporary SQLite database was seeded only from original synthetic CSVs and four synthetic users. The recorded original private backup was verified. A separate SQLite snapshot was taken before component calls with integrity_check=ok, outside the repository; its SHA256 is `56cdfed11204a335f89fea60e785e0ba367e7e40e71ad15c9f7b02b311785801`. Postflight confirms 80 articles, 500 tickets and four users, identical eligible records, unchanged seeded database main file/snapshot and restored temporary patches. The working database and baseline application hashes are unchanged; main-file hashes do not cover unrelated concurrent WAL writes. Private paths remain in isolated_database_backup.json and execution.json, not database contents.

Execution started 2026-09-22T19:08:27.263534+00:00 and finished 2026-09-22T19:08:51.940824+00:00 UTC. Parent elapsed time 26.493 seconds, exit0, no timeout. Recorded get_model() call duration 0.422 seconds excludes earlier import time; it is not total startup time.

The screen-flicker result is a confirmed reliability defect. Plausible consequences include unnecessary troubleshooting or delayed appropriate review if used; no user action, injury, unauthorized access or disclosure occurred. It was observed once on this bounded sample, so general prevalence and exploitability are unmeasured. Security severity remains Informational for the demonstrated observation; no formal vulnerability or risk product is assigned. This does not make the failed grounding behavior acceptable.

Recommended changes are not applied: retain the correct inclusive comparisons, add their regression coverage when fixes are authorized, check actual symptom/action support separately from score, abstain when evidence is insufficient, and constrain fuzzy correction of valid meaningful words. Describe source types accurately and avoid treating ranking percentages as probabilities. Threshold calibration requires an independent labelled validation dataset; these fixtures and selected queries do not justify changing weights or cutoffs.

## Evidence and reproduction

| Artifacts | Purpose |
|---|---|
| inputs.json, expected_result.md | Exact 16 inputs, selection window and rules fixed before execution |
| effective_configuration.json, preconditions.json | Actual nonsecret settings, source/main DB and original backup checks |
| eligible_records.json, corpus_preflight.json | Full original eligible text and CSV equality |
| isolated_database_backup.json, postflight.json | Seeded snapshot and post-call preservation/restoration |
| natural/N01.json through N16.json | Original normalization, retained-source order, native/pretrust/final scores, full retrieved text and four selected solutions |
| natural_summary.json, natural_selection.json | All scores and deterministic selections saved before answer calls |
| controlled_inputs.json, controlled/*.json | Declared injected targets and original comparison/solution results, explicit synthetic provenance |
| score_comparison.json/CSV, boundary_comparison.json/CSV | Later derived tables for 80 natural result rows and six boundary cases |
| answer_grounding_review.json, normalization_observations.json | Selected-answer claim mapping and observed input transformations |
| execution.json, process_result.json, terminal_log.txt | Counts, timing, provider state, completion and original integrity observations |
| review.json, evidence_integrity.json, notes.md | Separate reviewed verdict and raw/prior-evidence preservation |

Already executed once; rerunning creates new evidence and a new temporary database:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir12.py
~~~

No page/endpoint is used in this branch/component test. It is not equivalent to POST /tickets/create or an authenticated API request. The original application functions are in [retrieval_agent.py](../../../../app/agents/retrieval_agent.py) (adjustment line101, comparisons113/115), [solution_agent.py](../../../../app/agents/solution_agent.py) (gate line9, first-three selection30) and [hybrid_search.py](../../../../app/services/hybrid_search.py) (normalization97). No application files were edited.

**Conclusion:** numeric boundary logic PASS, selected natural-answer grounding FAIL. Raw captures remain Unassessed as originally collected; review.json supplies this later split verdict. Earlier cases remain unchanged. IR-13 through IR-15 are unexecuted; stop before IR-13.
