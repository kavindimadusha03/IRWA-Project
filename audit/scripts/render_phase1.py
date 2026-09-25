"""Render audit documentation from recorded Phase 1 evidence; do not invent missing results."""
from pathlib import Path
import json
import re
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"audit"
BASE=AUDIT/"evidence"/"baseline"
LOW=BASE/"low_memory"
def read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
def write(name,text):
    (AUDIT/name).write_text(text.strip()+"\n",encoding="utf-8")
env=read(BASE/"environment.json")
tests=read(BASE/"pytest_result.json")
evaluation=read(LOW/"ir_evaluation_result.json")
smoke=read(LOW/"application_baseline.json")
backup=read(BASE/"database_backup.json")
c=env["configuration"]
p=env["packages"]
readme="""# KnowGap AI: individual audit workspace

Specialization: Information Retrieval and Security Assessment.

This workspace records Phase 1 preparation and actual baseline attempts. Application source, access rules, ranking weights, confidence thresholds and Windows settings were not changed.

Start with [baseline.md](baseline.md) for actual results and [commands.md](commands.md) for exact beginner commands.

- [endpoint_inventory.md](endpoint_inventory.md): endpoints, Public/Authenticated/Role-restricted classification, role and input.
- [component_inventory.md](component_inventory.md): files, actual function flow and implemented improvements.
- [test_plan.md](test_plan.md): expected behavior and PASS/FAIL rules before attacks.
- [test_results.md](test_results.md): 15-case tracker and complete result templates.
- [vulnerability_register.md](vulnerability_register.md): confirmed weaknesses only.
- [risk_matrix.md](risk_matrix.md): justified risk assessment.
- [viva_notes.md](viva_notes.md): baseline explanations.
- evidence/baseline/: actual observations, redacted logs and integrity checks.
- evidence/IR-01/ through evidence/IR-15/: reserved evidence directories.
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

The 15 audit cases are still Not run. Normal baseline checks do not count as IR-01, IR-13 or another completed security test. Stop after Phase 1 and wait for “Continue to IR-01”.

Suggested commit message after reviewing only audit files: docs: record Phase 1 IR security audit baseline
"""
write("README.md",readme)
initial_native={"recorded_at_utc":datetime.now(timezone.utc).isoformat(),"source":"Transcription of actual exec tool output, session 84409; child exited before Python evidence writer could finish","action":"initial IR evaluation, normal numerical thread settings","exit_code":1,"stderr":["OpenBLAS error: Memory allocation still failed after 10 retries, giving up.","OpenBLAS error: Memory allocation still failed after 10 retries, giving up."],"metrics_produced":False}
(BASE/"initial_evaluation_native_failure.json").write_text(json.dumps(initial_native,indent=2)+"\n",encoding="utf-8")
lines=["# Phase 1 baseline: actual observations","",
"Phase 1 preparation and baseline attempts are recorded. The baseline is **not ready for security-test interpretation**: Windows memory failures prevented retrieval evaluation, login verification and known-query verification. No metric or success is invented.",
"",f"Environment captured at {env['recorded_at_utc']}. Evidence timestamps are UTC.","","## System configuration","",
"| Setting | Observed value | Evidence |","|---|---|---|"]
system=[("Python",env["python"]),("FastAPI",p["fastapi"]),("SQLModel",p["sqlmodel"]),("sentence-transformers",p["sentence-transformers"]),("rank_bm25 (distribution rank-bm25)",p["rank-bm25"]),("pytest",p["pytest"]),("Uvicorn",p["uvicorn"]),("Operating system",env["operating_system"]),("Database type",c["database_type"]),("Embedding model",c["embedding_model"]),("Configured LLM model",c["llm_model"]),("Normal localhost URL",env["localhost_url"]),("Isolated baseline URL",smoke.get("localhost_url","Not established"))]
lines += [f"| {a} | {b} | evidence/baseline/environment.json or low_memory/application_baseline.json |" for a,b in system]
lines += ["","SECRET_KEY and GROQ_API_KEY entries exist. Values are not recorded. The test process reported llm.enabled=false; model name is configuration, not proof of a successful provider request.","","## Retrieval configuration","",
"| Setting | Current Value | File |","|---|---|---|",
"| BM25 tokenization | Lowercase; regex technical/hex tokens; selected punctuation preserved; slash components | app/services/bm25.py:7-47 |",
"| Query preprocessing | Phrase/abbreviation/typo replacements, filler removal, fuzzy cutoff 0.72, repeated-token removal | app/services/hybrid_search.py:97-153 |",
f"| Embedding model | {c['embedding_model']} | app/services/embeddings.py:11 |",
f"| Hybrid BM25 weight | {c['hybrid_bm25_weight']} (effective value) | app/config.py:16 |",
f"| Hybrid semantic weight | {c['hybrid_semantic_weight']} (effective value) | app/config.py:17 |",
f"| HIGH threshold | >= {c['high_threshold']} (effective value) | app/config.py:18; retrieval_agent.py:113 |",
f"| UNCERTAIN threshold | >= {c['uncertain_threshold']} and below HIGH (effective value) | app/config.py:19; retrieval_agent.py:115 |",
"| top-k | Ticket/direct retrieval 5; chat 3; recommendation uses first 3 sources | coordinator.py:54; retrieval_agent.py:92; chat.py:60; solution_agent.py:30 |",
"| Source trust weights | Draft 0; approved or internal_kb 1; resolved or resolved_ticket 0.85; other 0.7, in that branch order | app/agents/retrieval_agent.py:43-53 |",
"| Exact error-code boost | +0.35 for matching hexadecimal code | app/services/hybrid_search.py:222-230 |",
"| Metadata eligibility | Approved KB; RESOLVED tickets with nonblank resolution; no per-user/security-class filter | app/agents/retrieval_agent.py:56-89 |",
"| Metadata ranking | Category +0.18; selected OS +0.14 to +0.18; approved/resolved +0.08; shortlist boosts, not hard category/OS filters | app/agents/retrieval_agent.py:17-40,94-110 |",
"| Duplicate handling | First normalized title/content match retained; same-category content Jaccard >=0.9 removed | app/services/hybrid_search.py:162-201 |",
"| Model/document cache | Model maxsize=1; whole ordered corpus tuples maxsize=128; query re-encoded | app/services/embeddings.py:9-44 |",
"","Settings above came from effective nonsecret configuration inspection plus fixed source parameters. Scores can exceed 1 and are not probabilities. No parameter was retuned.","",
"## Database and accounts","",
"knowgap.db exists and was opened using a read-only SQLite URI with uri=True and PRAGMA query_only=ON. No rows were edited.","",
"Tables: "+", ".join(env["database"]["tables"])+".","",
"| Table | Existing database count |","|---|---|"]
lines += [f"| {name} | {count} |" for name,count in env["database"]["counts"].items()]
lines += ["","| Role | Active accounts |","|---|---|"]+[f"| {r['role']} | {r['count']} |" for r in env["database"]["role_counts"] if r["active"]]
lines += ["","All four required roles exist. Role presence does not prove login succeeds. No existing usernames, hashes or passwords are included.","",
f"Private backup created with sqlite3.Connection.backup(); integrity_check returned {backup.get('integrity_check')}. Its location and SHA-256 are recorded in evidence/baseline/database_backup.json. Keep the actual backup outside Git and report submissions.","",
"CSV counts: 80 KB articles, 500 historical tickets and 21 gold queries. The existing database has 81 KB articles and 528 tickets. Runtime baseline fixtures use the CSV data only.","",
"## Actual automated-test result","",
f"- Result: {'; '.join(tests.get('summary_lines',[]))}.",
f"- Exit code: {tests.get('exit_code')}. Total helper duration: {tests.get('elapsed_seconds')} seconds.",
"- Existing test source was unchanged; the configured application database was replaced only inside the test process with a temporary SQLite file.",
"- Pytest cache output was disabled. Model loading used the existing local cache.",
"- Evidence: evidence/baseline/pytest_output.txt and pytest_result.json.",
"- All five failures reached model loading and raised Windows OSError 1455: The paging file is too small for this operation to complete.",
"- This is an environment/reliability blocker, not five demonstrated security vulnerabilities. Failed embedding tests do not establish incorrect ranking behavior.",
"",
"Failed test names:",""]
test_log=(BASE/"pytest_output.txt").read_text(encoding="utf-8")
lines += ["- "+line.removeprefix("FAILED ") for line in test_log.splitlines() if line.startswith("FAILED ")]
lines += ["",f"LLM observation: configured_enabled={tests.get('llm',{}).get('configured_enabled')}; attempts={tests.get('llm',{}).get('attempts')}; successful chat returns={tests.get('llm',{}).get('successes')}; error types={tests.get('llm',{}).get('error_types')}. Exceptions exercised the application's fallback. A successful chat return would not alone prove valid JSON parsing or answer adoption.","",
"## Actual IR evaluation attempt","",
"Initial attempt exited with native OpenBLAS memory-allocation errors before metrics. A separate one-thread retry also exited 1 with Windows paging-file error 1455 while loading MiniLM. Neither attempt produced numeric metrics.","",
"| Method | P@1 | P@5 | Recall@5 | MRR | Other metrics |","|---|---|---|---|---|---|"]
metrics=evaluation.get("metrics_as_printed",[])
if metrics:
    lines += [f"| {m['method']} | {m['P@1']} | {m['P@5']} | {m['Recall@5']} | {m['MRR']} | Not implemented |" for m in metrics]
else:
    lines += [f"| {method} | Unavailable | Unavailable | Unavailable | Unavailable | Hit Rate/nDCG not implemented |" for method in ("BM25","Semantic","Hybrid")]
lines += ["","Unavailable means no score was produced; it does not mean zero accuracy.","",
"Evidence: initial_evaluation_native_failure.json; low_memory/ir_evaluation_output.txt, ir_evaluation_result.json and evaluation_process_result.json.","",
"Metric meanings: P@1 is first-result relevance; P@5 is relevant hits among five divided by five; Recall@5 is relevant hits divided by the labelled relevant set; MRR averages reciprocal rank of the first relevant result across the full ranking.","",
"The evaluator uses approved CSV articles, raw query scoring and fixed BM25/semantic weights 0.45/0.55. There is no weight sweep. It omits the application's normalization, deduplication, exact-code bonus, trust/metadata adjustments, historical tickets and confidence decisions. Even its BM25 branch computes semantic scores. Duplicate labels can omit equivalent answers, and an empty relevance set receives zeros without assessing abstention.","",
"## Application startup, login and known-query evidence","",
f"Bound only to {smoke.get('localhost_url','unavailable')} using a reserved socket. Port 8000 was occupied, so the audit used 8001 without interacting with the existing server. Database fixtures were synthetic and separate.","",
"| Baseline check | Actual observation | Interpretation |","|---|---|---|"]
checks=smoke.get("checks",{})
for key,label in [("startup","Startup /health"),("swagger","Swagger /docs"),("registration","Synthetic registration"),("login","Valid login"),("known_retrieval","Known Wi-Fi retrieval"),("ticket_workflow","Ticket workflow")]:
    result=checks.get(key)
    if result is not None:
        value=json.dumps(result,ensure_ascii=False)
        interpretation="Observed positive check passed" if result.get("passed") else "Did not meet baseline expectation"
    else:
        value="No completed result recorded"
        interpretation="Unverified; baseline stopped before completion"
    lines.append(f"| {label} | {value} | {interpretation} |")
lines += ["",
"Registration's HTTP 500 is linked in application_output.txt to argon2.exceptions.HashingError: Memory allocation error. The subsequent request failed with a connection ReadError; no successful login is claimed. Known retrieval and ticket creation were not reached in this baseline run.",
"",
"Expected normal query (fixed before execution): My laptop is connected to Wi-Fi, but websites do not load and there is no internet access. Expected evidence: a relevant approved Wi-Fi guide. This expected result is not an observed result.",
"",
f"Audit server stopped: {smoke.get('server_stopped')}. Evidence: low_memory/application_baseline.json, application_output.txt and smoke_process_result.json. No browser screenshot was captured.",
"",
"## Integrity and readiness","",
"Completed collection actions recorded unchanged application/data/evaluation/test source hashes and unchanged original knowgap.db main-file hashes. The helper never opens that original file for writes. Checksums do not cover concurrent WAL changes by the user's separate running instance.",
"",
"- Source/configuration, endpoint/component inventories, database tables/roles, backup and test preparation: recorded.",
"- Existing test run: completed with real failures preserved.",
"- IR evaluation: attempted twice; unavailable due memory exhaustion.",
"- Startup and Swagger: observed working on the isolated instance.",
"- Login and known retrieval: not established.",
"- Groq generation: unavailable in the loaded configuration; fallback only.",
"- IR-01 through IR-15: Not run; no attack executed.",
"",
"Resolve memory availability before drawing retrieval/security conclusions from new executions. Do not lower password-hashing settings, replace embeddings or modify ranking to hide this baseline. Preserve these logs when recording a later successful baseline.",
"",
"Source-review concerns in endpoint_inventory.md and component_inventory.md remain candidates for later tests. No vulnerability severity is assigned merely because these baseline checks failed."]
write("baseline.md","\n".join(lines))
cases=[
("IR-01","Exact Known Issue Retrieval","Retrieval accuracy"),
("IR-02","Paraphrased Query Retrieval","Semantic accuracy"),
("IR-03","Exact Technical Error Code","Technical-token accuracy"),
("IR-04","Unknown / Unsupported Query","Safe escalation"),
("IR-05","Keyword Stuffing","Retrieval manipulation"),
("IR-06","Conflicting Category Keywords","Ambiguity/manipulation"),
("IR-07","Long Noisy Query","Retrieval robustness"),
("IR-08","Error-Code Formatting Variations","Formatting robustness"),
("IR-09","Draft / Unapproved KB Exclusion","Source approval"),
("IR-10","Source Reliability / Trust","Source authority"),
("IR-11","Retrieval-Induced Hallucination","Grounded answers"),
("IR-12","Confidence Threshold Boundary","Confidence decisions"),
("IR-13","Unauthenticated Access","Authentication"),
("IR-14","Unauthorized Role Access","Authorization"),
("IR-15","API Input Validation / Security","API and agent communication"),
]
result_lines=["# Audit test results","","These are unexecuted case records, not baseline unit-test results. See baseline.md for the separate Phase 1 executions.","","| Test ID | Area | Status | Evidence | Pass/Fail | Vulnerability |","|---|---|---|---|---|---|"]
for ident,name,area in cases:
    result_lines.append(f"| {ident} | {area} | Not run | evidence/{ident}/ (reserved; none captured) | Unassessed | Unassessed |")
for ident,name,area in cases:
    result_lines += ["",f"## {ident} — {name}","",
    f"- Test ID: {ident}",f"- Test Name: {name}",
    "- Test Objective: Defined in the matching test_plan.md case.",
    "- Component Being Tested: Defined in test_plan.md.",
    "- Input / Attack Scenario: Planned in test_plan.md; save the exact executed input later.",
    "- Preconditions: Not yet verified for this case; baseline memory blocker remains.",
    "- Steps: Planned in test_plan.md; not executed.",
    "- Expected Behaviour: Defined before execution in test_plan.md.",
    "- Actual Behaviour: Not run.",
    "- Evidence: None captured for this case.",
    "- Observation: Pending.",
    "- Outcome: Unassessed.",
    "- Vulnerability Identified: Unassessed.",
    "- Impact: Unassessed.",
    "- Likelihood: Unassessed.",
    "- Severity: Unassessed.",
    "- Technical Explanation: Pending actual evidence.",
    "- Recommended Mitigation: Pending a demonstrated weakness.",
    "- Conclusion: No PASS/FAIL or vulnerability claim yet."]
write("test_results.md","\n".join(result_lines))
write("vulnerability_register.md","""# Vulnerability register

No runtime-validated vulnerability entries have been created during Phase 1. This does not establish that the system is secure.

Source concerns are documented in endpoint_inventory.md and component_inventory.md for subsequent tests. Baseline memory errors are recorded as execution/reliability limitations in baseline.md, not automatically as vulnerabilities.

When evidence supports a finding, record: Vulnerability ID; Title; Related Test; Affected Component; Description; Evidence; Impact; Likelihood; Severity; Risk Level; Technical Explanation; Recommended Mitigation; Status.

Use only Critical, High, Medium, Low or Informational, with explicit justification. Do not assign a risk from a failed unit assertion alone.
""")
write("risk_matrix.md","""# Risk matrix

No validated vulnerability is rated in Phase 1. The empty matrix is intentional.

| Vulnerability | Impact | Likelihood | Severity / Risk Level | Recommended Mitigation |
|---|---|---|---|---|

Critical requires very serious impact and realistic exploitation. High requires major impact and plausible exploitation. Medium describes a meaningful but limited weakness. Low has limited impact or difficult exploitation. Informational describes an observation without meaningful immediate security impact.

Assess impact and likelihood from the demonstrated scenario, data exposure, privilege required and controls that actually apply. Explain uncertainty. A baseline environment failure alone is not proof of attacker-induced denial of service.
""")
write("viva_notes.md","""# Phase 1 viva preparation

These notes cover completed preparation only. Attack success, most serious vulnerability and final mitigation rankings remain unanswered until testing.

| Question | Short answer | Follow-up explanation |
|---|---|---|
| What is your specialization? | Information Retrieval and Security Assessment. | I assess accuracy, manipulation, grounding, source trust, authentication, authorization, APIs and agent communication. |
| How does retrieval work? | It combines word matching and meaning matching. | search_knowledge loads approved KB/resolved tickets; hybrid_rank deduplicates, preprocesses, combines BM25 and semantic scores, and boosts exact codes; trust/metadata rerank the shortlist. |
| What is BM25? | A lexical relevance method. | It scores query words using term occurrence and document statistics. This implementation normalizes its scores before combining them. |
| What is an embedding? | A numerical representation of text. | MiniLM creates vectors; cosine similarity compares their directions for semantic retrieval. |
| Why hybrid retrieval? | Exact terms and paraphrases need different matching strengths. | This is a design motivation, not proof that the current weights are optimal. No weight sweep exists. |
| Is confidence a probability? | No. | It is a score after weighting and bonuses; it may exceed one. HIGH does not prove truth. |
| Authentication versus authorization? | Identity versus permission. | A JWT cookie identifies the database user; individual handlers check current role and sometimes ticket ownership. |
| Are agents independent secure services? | No; the main workflow calls Python functions. | Direct REST endpoints also exist. Their message fields do not authenticate sender identity. |
| What did Phase 1 prove? | It recorded source structure, configuration, tables/roles and actual baseline attempts. | Startup and Swagger worked; tests had 9 passes/5 memory-related failures; no IR scores or successful login/retrieval baseline were produced. |
| Why no IR metrics? | MiniLM could not load because of Windows memory/paging limits. | Even the evaluator's BM25 branch computes semantic scores. Unavailable scores must not be written as zero. |
| Was a vulnerability confirmed? | No attack case has run yet. | Source concerns remain documented candidates. Environment failures do not automatically prove security weaknesses. |
| Responsible AI implications? | Answers need relevant evidence, honest uncertainty and appropriate escalation. | Transparency is limited when the UI displays aggregate confidence without component scores or provenance validation. Impact requires later tests. |

After testing, expand these notes with the actual successful/failed attacks, justified severity decisions and mitigation tradeoffs.
""")
write("commands.md",r"""# Exact Phase 1 commands and expected evidence

Run PowerShell in the project folder. A virtual environment is the project's separate Python package environment.

## Activate and verify

~~~powershell
Set-Location 'C:\Users\PSB\Desktop\KnowGap\IRWA-Project'
.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
~~~

Expect Python 3.12.10 and an executable under .venv. If activation is blocked, replace python below with .\.venv\Scripts\python.exe; no system execution-policy change is required.

## Read-only SQLite table check

~~~powershell
python -c "import sqlite3; db=sqlite3.connect('file:knowgap.db?mode=ro', uri=True); print(db.execute('SELECT name FROM sqlite_master WHERE type = ?', ('table',)).fetchall()); db.close()"
~~~

This opens the existing file read-only and lists table names without row data. URI handling requires uri=True.

For a saved nonsecret environment/table/role snapshot:

~~~powershell
python -B audit/scripts/collect_baseline.py inspect
~~~

Expect evidence/baseline/environment.json and workspace_files.txt. Snapshot commands overwrite their prior names; preserve a dated copy before a later baseline.

## Consistent database backup

~~~powershell
python -B audit/scripts/collect_baseline.py backup
~~~

The helper uses SQLite's backup API from a read-only source. It places a private backup in a new temporary directory outside the repository, verifies integrity and records only its path/hash in evidence/baseline/database_backup.json. Retain the backup privately before destructive tests.

## Start FastAPI and open Swagger manually

~~~powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
~~~

Expect application-startup messages. This manual command uses the ordinary configured database. The baseline helper instead uses a separate synthetic database. Do not stop an existing unrelated server to free its port.

In another terminal:

~~~powershell
Start-Process 'http://127.0.0.1:8000/docs'
~~~

Expect Swagger's endpoint list. Save a screenshot only if observed; exclude cookies and credentials. Opening /dashboard also executes the IR evaluator and is not a passive check.

## Existing automated tests, isolated from the working database

~~~powershell
python -B audit/scripts/run_baseline.py tests
~~~

The helper runs the existing unmodified tests with pytest -q -p no:cacheprovider tests after setting a temporary DATABASE_URL before application imports. It does not change the configured Groq key. It records whether calls succeeded or fell back, without saving credentials.

Do not run plain pytest against the working database: the notification test commits user/ticket/notification records without cleanup.

Expect an actual pytest summary, not necessarily passing tests. Save pytest_output.txt, pytest_result.json and tests_process_result.json. The recorded baseline was 9 passed and 5 failed due model-loading memory errors.

## Existing IR evaluation

Original project command:

~~~powershell
python evaluation/evaluate_ir.py
~~~

This may contact the model host to download missing files. For the recorded cached-model-only baseline with saved native output:

~~~powershell
python -B audit/scripts/run_baseline.py evaluation
~~~

It executes the original evaluation script and saves actual printed metrics or the actual error. Expect columns Method, P@1, P@5, Recall@5 and MRR if loading succeeds. No numeric metrics were obtained in this baseline.

The recorded retry limited numerical-library threads:

~~~powershell
python -B audit/scripts/run_baseline.py evaluation --low-memory
~~~

Its evidence is saved separately under evidence/baseline/low_memory/. It also failed with paging-file error 1455. This is not a different ranking/model implementation.

## Normal startup/login/retrieval baseline on synthetic data

~~~powershell
python -B audit/scripts/run_baseline.py smoke --low-memory
~~~

This seeds a separate temporary database from the synthetic CSVs, binds an available loopback port (8000, 8001 or 8002), checks health/docs, attempts a synthetic registration/login and one normal Wi-Fi query, then stops its own server. Credentials stay in memory; no browser cookies are saved.

Expect application_baseline.json and redacted server/process logs under evidence/baseline/low_memory/. Current evidence: startup/docs HTTP 200; registration HTTP 500 from Argon2 memory allocation; login unverified and known retrieval not reached. Do not treat this command as IR-01 completion.

## What to capture and what to do next

Preserve the current evidence before rerunning. Capture full redacted terminal output, actual status/exit codes and later genuine screenshots. Do not invent a successful result when a dependency fails.

Address Windows memory availability before interpreting further retrieval tests. No Windows paging settings, password-hashing parameters, embedding code or ranking rules were changed here.

Stop after Phase 1. Start the first individual audit case only after “Continue to IR-01”.
""")
write("evidence/README.md","""# Evidence index

baseline/ contains actual Phase 1 observations, logs and JSON results. low_memory/ holds the separately labelled reduced-thread retries. The initial native evaluation failure is explicitly labelled a transcription from the execution tool because the process exited before its own writer completed.

IR-01/ through IR-15/ contain .gitkeep placeholders only. Directory existence is not test evidence. No screenshots were captured or fabricated.

The private database backup and temporary runtime/test databases are outside this folder. Never copy them here for submission. Never store keys, passwords, cookies, JWTs or .env contents.
""")
print("Rendered README.md, baseline.md, commands.md, test_results.md, vulnerability_register.md, risk_matrix.md, viva_notes.md and evidence/README.md from actual evidence.")
