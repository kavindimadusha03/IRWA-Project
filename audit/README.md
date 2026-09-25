# KnowGap AI: individual audit workspace

Specialization: Information Retrieval and Security Assessment.

This workspace records Phase 1 preparation, actual baseline attempts and the completed IR-01, IR-02 and IR-04 through IR-13 cases, and the partially assessed IR-03, IR-14 and IR-15 cases. IR-14 route checks pass; IR-15 confirms a component evidence-trust failure; their full-app verification remains blocked. Application source, access rules, ranking weights, confidence thresholds and Windows settings were not changed.

The final eight-section report is available as [Markdown](final_report.md), an [editable Word document](final_report.docx), and [printable HTML](final_report.html). The report records all 15 case IDs, including the three partial cases and two open Medium findings. Aggregate IR metrics remain unavailable; no test result was invented or remediation applied. Keep these files in this audit directory alongside the linked evidence. Open the HTML in a browser and use Print / Save as PDF if a PDF copy is required. Export content and evidence hashes are recorded in [final_report_manifest.json](final_report_manifest.json).

Start with [baseline.md](baseline.md) for actual results and [commands.md](commands.md) for exact beginner commands.

- [endpoint_inventory.md](endpoint_inventory.md): endpoints, Public/Authenticated/Role-restricted classification, role and input.
- [component_inventory.md](component_inventory.md): files, actual function flow and implemented improvements.
- [test_plan.md](test_plan.md): expected behavior and PASS/FAIL rules before attacks.
- [test_results.md](test_results.md): 15-case tracker and complete result templates.
- [vulnerability_register.md](vulnerability_register.md): confirmed weaknesses only.
- [risk_matrix.md](risk_matrix.md): justified risk assessment.
- [viva_notes.md](viva_notes.md): baseline explanations.
- evidence/baseline/: actual observations, redacted logs and integrity checks.
- evidence/IR-01/ through evidence/IR-15/: actual case evidence, including retrieval checks, missing agent authentication, scoped role checks and a confirmed component evidence-trust failure; partial scope and startup limitations remain explicit.
- scripts/: audit-only helpers.

## Scope

In scope: retrieval accuracy; retrieval manipulation; retrieval-induced hallucination; source reliability; authentication; authorization; API security; agent communication security.

Out of scope: external/public systems; university infrastructure; production penetration testing; denial-of-service testing against third-party services; real user data.

The existing database is inspected only for aggregate counts, tables and role presence. Runtime checks use a temporary SQLite database containing only the project's synthetic CSVs and test accounts. The private database backup is outside the repository and must never be submitted as evidence. Normal synthetic Groq calls are not attacks on the external service; provider availability is recorded separately.

## Limitations

- Synthetic data and 21 gold queries have limited coverage and do not represent all IT incidents.
- This is a Windows localhost development environment, not an enterprise deployment.
- No external production users or infrastructure form part of the tested instance.
- Existing database counts differ from CSV counts. Runtime synthetic checks do not validate every working-database record.
- Groq availability affects generated answers; fallback behavior is not live LLM assurance.
- The embedding model is loaded from the existing cache with HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1. No substitute model is used.
- The reduced-thread retry sets OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and NUMEXPR_NUM_THREADS to 1 in its own process.
- Working-database main-file hashes do not prove absence of concurrent WAL changes by another application instance.
- No screenshot was fabricated. HTTP logs establish response observations, not browser layout.
- CSV evaluation is simpler than the application retrieval pipeline, has duplicate-label limitations, and does not evaluate safe abstention.

## Evidence and Git

Do not save .env contents, keys, passwords, JWTs, cookies or reset links. Do not commit knowgap.db, backups, .venv, __pycache__ or .pytest_cache.

The helper stores only role/count summaries from existing accounts. A random synthetic account password is held in memory and is not saved. Test and evaluation output is redacted before writing.

Source hashes cover app/, data/, evaluation/ and tests/. Each completed collection action compares the original database main file and source hashes. Temporary audit databases remain outside the repository.

IR-01 passed in the configured fallback mode: model loading, normal login and one known-query ticket succeeded. See [evidence/IR-01/run-20260921T194038486465Z/notes.md](evidence/IR-01/run-20260921T194038486465Z/notes.md). IR-02 also passed in hybrid/fallback mode; see [evidence/IR-02/run-20260921T200014957237Z/notes.md](evidence/IR-02/run-20260921T200014957237Z/notes.md). IR-03 preserved the code but cannot establish exact-source matching: no eligible exact-code source exists. See [evidence/IR-03/run-20260922T025949665873Z/notes.md](evidence/IR-03/run-20260922T025949665873Z/notes.md) for its partial/Inconclusive result and confidence observation. IR-04 passed: insufficient evidence was explained and the unsupported ticket reached the IT Support queue; see [evidence/IR-04/run-20260922T032828639324Z/notes.md](evidence/IR-04/run-20260922T032828639324Z/notes.md). IR-05 passed the fixed clear-printer comparison, with classification/display observations and exploratory limits; see [evidence/IR-05/run-20260922T035809651634Z/notes.md](evidence/IR-05/run-20260922T035809651634Z/notes.md). IR-06 failed ambiguity handling in fallback mode: confident mixed repairs were presented without clarification or escalation; see [evidence/IR-06/run-20260922T080545264958Z/notes.md](evidence/IR-06/run-20260922T080545264958Z/notes.md). No security exploit was demonstrated. IR-07 passed the bounded noisy-printer case; the 1099-character input becomes a 180-character retrieval prefix. See [evidence/IR-07/run-20260922T131456012577Z/notes.md](evidence/IR-07/run-20260922T131456012577Z/notes.md). IR-08 passed retrieval formatting with a labelled isolated fixture; uppercase entity extraction failed separately. See [evidence/IR-08/run-20260922T132754058395Z/notes.md](evidence/IR-08/run-20260922T132754058395Z/notes.md). No code-specific repair is validated and IR-03 remains unchanged. IR-09 passed draft exclusion and approved-control availability; unrelated secondary advice is a separate quality observation. See [evidence/IR-09/run-20260922T140938591791Z/notes.md](evidence/IR-09/run-20260922T140938591791Z/notes.md). IR-10 passed documented trust weighting and negative-control exclusion in a fixture-only fallback case; equal-score preference is derived arithmetic, not an observed equal-relevance trial. See [evidence/IR-10/run-20260922T143655875673Z/notes.md](evidence/IR-10/run-20260922T143655875673Z/notes.md). IR-11 failed fallback grounding: update history was presented as applicable to battery swelling without support or escalation; no provider answer was adopted. See [evidence/IR-11/run-20260922T183346970504Z/notes.md](evidence/IR-11/run-20260922T183346970504Z/notes.md). IR-12 passed inclusive threshold branches (16 natural searches, six exact score fixtures) while a selected HIGH screen-flicker answer failed grounding; no HTTP/ticket routing was tested. See [evidence/IR-12/run-20260922T190826464494Z/notes.md](evidence/IR-12/run-20260922T190826464494Z/notes.md). IR-13 failed: two agent APIs returned internal synthetic source/analytics data anonymously, while UI denial held. VULN-IR13-01 is confirmed Medium; see [evidence/IR-13/run-20260922T193751545217Z/notes.md](evidence/IR-13/run-20260922T193751545217Z/notes.md). IR-14 is partially assessed: all 15 original-router HTTP role checks PASS, while full-app startup is blocked by Windows Application Control (WinError 4551). No new vulnerability identified; VULN-IR13-01 remains open. IR-15 is partially assessed: selected-handler/schema/component checks demonstrate VULN-IR15-01 (Medium), caller-supplied evidence trusted by the original solution component; full app and actual retrieval remain blocked. All 15 core IDs have evidence; IR-03, IR-14 and IR-15 retain partial scope limits. See [evidence/IR-15/run-20260923T023805163543Z/notes.md](evidence/IR-15/run-20260923T023805163543Z/notes.md). See [evidence/IR-14/run-20260923T021324976415Z/notes.md](evidence/IR-14/run-20260923T021324976415Z/notes.md). No later case will run until requested. Phase 1 failures remain preserved; these individual case runs do not replace the earlier test suite or IR evaluation results.

Suggested commit message after reviewing only audit files: docs: record Phase 1 IR security audit baseline
