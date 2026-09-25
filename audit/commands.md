# Exact Phase 1 commands and expected evidence

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

## IR-01 reproduction after explicit case authorization

~~~powershell
python -B audit/scripts/run_ir01.py
~~~

This loads the cached model, seeds a new temporary synthetic database, logs in using the seeded CUSTOMER, submits exactly one normal Wi-Fi ticket, captures unmodified return values and the HTTP ticket page, and stops its own server. Every run saves a new timestamped folder beneath evidence/IR-01/. It does not rerun the 15 cases.

The recorded case is [evidence/IR-01/run-20260921T194038486465Z/notes.md](evidence/IR-01/run-20260921T194038486465Z/notes.md). Read it before deciding to rerun anything. Phase 1 failures are historical records, and the Phase 1 report renderer must not be rerun to reset completed test records.

## IR-02 reproduction after explicit case authorization

~~~powershell
python -B audit/scripts/run_ir02.py
~~~

This runs one paraphrased ticket on a fresh synthetic database, first checking source/CSV hashes and effective settings against IR-01. It saves normalized query, original returned scores, answer and HTTP page in a new IR-02 timestamped folder. See [evidence/IR-02/run-20260921T200014957237Z/notes.md](evidence/IR-02/run-20260921T200014957237Z/notes.md) for the already completed case; no rerun is needed to read the result. No other audit case is executed by this command.

## IR-03 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir03.py
~~~

Run from the project root. This submits one technical-code ticket on a fresh synthetic database and records original code processing, eligible corpus, ranking, answer and HTTP page. No exact-code source is injected. Each execution creates a new timestamped IR-03 folder. The already saved [evidence/IR-03/run-20260922T025949665873Z/notes.md](evidence/IR-03/run-20260922T025949665873Z/notes.md) records the partial/Inconclusive outcome; no rerun is needed to read it. No later case executes.

## IR-04 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir04.py
~~~

Run from the project root. This submits one unsupported battery-swelling query on a fresh synthetic database and records corpus coverage, original retrieval/answer, customer HTML and a normally authenticated read of the IT Support queue. It does not resolve, approve or manually escalate the ticket. Each run creates a new IR-04 timestamped folder. See the already completed [evidence/IR-04/run-20260922T032828639324Z/notes.md](evidence/IR-04/run-20260922T032828639324Z/notes.md); no rerun is needed to read the result. No later case executes.

## IR-05 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir05.py
~~~

Runs the planned baseline, appended-VPN variant and separately labelled exploratory phrase once each on independent synthetic databases with identical corpus/settings. Saves original analysis, normalization, ranking, answer and HTML under three subdirectories of a new IR-05 run. It does not execute IR-06 or later cases. The completed [evidence/IR-05/run-20260922T035809651634Z/notes.md](evidence/IR-05/run-20260922T035809651634Z/notes.md) can be read without rerunning.

## IR-06 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir06.py
~~~

Runs one ambiguous multi-category ticket on a fresh synthetic database and records original analysis, ranking, answer, stored state and customer/support HTML. No repair or support mutation is executed. A new timestamped evidence directory is created on rerun. Read the completed [evidence/IR-06/run-20260922T080545264958Z/notes.md](evidence/IR-06/run-20260922T080545264958Z/notes.md) for the actual scoped FAIL; no rerun is needed. IR-07 and later cases are not executed.

## IR-07 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir07.py
~~~

Submits one exact 1099-character noisy printer ticket to a fresh synthetic local database. Reuses the saved IR-05 short baseline after source/config/corpus checks, captures input lengths and original responses, then stops its server. A rerun creates a new timestamped folder; no rerun is needed to read the completed [evidence/IR-07/run-20260922T131456012577Z/notes.md](evidence/IR-07/run-20260922T131456012577Z/notes.md). IR-08 and later cases are not executed.

## IR-08 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir08.py
~~~

Executes five predeclared code-format variants once each, on five fresh temporary databases containing the same original synthetic corpus plus one labelled exact-code lookup fixture. Checks the existing private backup and preserves the working database, CSVs and application source. Saves original rankings, flags, answers, entities and HTTP pages; stops its servers. A rerun creates new evidence and is not needed to read the completed [evidence/IR-08/run-20260922T132754058395Z/notes.md](evidence/IR-08/run-20260922T132754058395Z/notes.md). IR-09 and later cases are not executed.

## IR-09 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir09.py
~~~

Submits the draft marker and approved-control marker once each using two fresh temporary databases with identical original synthetic data plus the same fixture pair. Verifies the private working-DB backup and creates an integrity-checked private snapshot of each seeded test DB before its request. Records full eligible corpora, unchanged statuses, original rankings/answers/citations and response-only leakage checks. No draft is approved; working data/source stays unchanged; servers stop after capture. A rerun creates new evidence; read [evidence/IR-09/run-20260922T140938591791Z/notes.md](evidence/IR-09/run-20260922T140938591791Z/notes.md) for the completed result. IR-10 and later cases are not executed.

## IR-10 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir10.py
~~~

Already executed once. A rerun creates a fresh fixture-only temporary database and new evidence, then submits one printer-queue ticket through a normal synthetic CUSTOMER login. The runner verifies the original private backup, creates a private fixture snapshot before the request, captures unchanged original scores/trust/metadata and checks statuses/negative controls. It reads the authenticated support queue and stops its server. It does not inject scores, approve sources, change working data or execute IR-11. See [evidence/IR-10/run-20260922T143655875673Z/notes.md](evidence/IR-10/run-20260922T143655875673Z/notes.md) for the completed PASS and limits. Derived score tables and report were produced afterward from saved evidence by record_ir10.py without a new retrieval request.

## IR-11 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir11.py
~~~

Already executed once. A rerun creates fresh evidence and an isolated synthetic database, verifies the recorded original backup, snapshots the seeded database and submits one fixed query through its owned localhost server. No source fixture or score substitution is used. It saves original retrieved text, scores, answer, provider-adoption checks and customer/support responses, then stops the server. Read [evidence/IR-11/run-20260922T183346970504Z/notes.md](evidence/IR-11/run-20260922T183346970504Z/notes.md) for the completed fallback-grounding FAIL. record_ir11.py derives the review from those captures without submitting a request. Do not rerun the completed report writer or proceed to IR-12 without its separate case authorization.

## IR-12 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir12.py
~~~

Already executed once. A rerun creates new evidence and a private temporary database seeded from original synthetic CSVs, verifies the original backup and snapshots the seeded database. It performs 16 fixed natural component searches, four deterministically selected solution calls and six labelled injected-score branch/solution checks. It does not send HTTP requests, create tickets, insert the control source into the DB or test support routing. Read [evidence/IR-12/run-20260922T190826464494Z/notes.md](evidence/IR-12/run-20260922T190826464494Z/notes.md) for the branch PASS and selected-answer grounding FAIL. record_ir12.py derives the report from saved data only; its completed writer must not be rerun. IR-13 and later are outside this runner.

## IR-13 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir13.py
~~~

Already executed once. A rerun creates fresh evidence and a private synthetic database, verifies the recorded original backup, starts its own loopback server, snapshots all tables, and sends one request each to GET /home, POST /tickets/create, POST /agents/retrieval/search and POST /agents/knowledge/analyze. Fresh clients send no authentication and do not follow redirects. Valid nonsecret request bodies are saved in inputs.json and each A01-A04/request.json. Table hashes are checked after each request and the server stops afterward. It does not log in, change roles, test other endpoints or fix authentication. Read [evidence/IR-13/run-20260922T193751545217Z/notes.md](evidence/IR-13/run-20260922T193751545217Z/notes.md) for the confirmed FAIL/Medium finding. record_ir13.py derives the report without new requests and must not be rerun after recording.

## IR-14 reproduction after explicit case authorization

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir14.py --route-harness
~~~

Already executed once in this explicit scope. The harness mounts the unchanged original auth, knowledge and admin routers, snapshots five private synthetic databases and sends five normal logins, five profile controls and 15 declared role checks. It saves nonsecret requests/responses and per-request state/identity checks, then stops its servers. All 15 route checks passed. No test credentials are printed.

The default command without --route-harness imports the full application; the preserved attempt was blocked with WinError 4551 on torch_python.dll before any HTTP. The flag selects a documented router-level test and does not fix or certify full-app startup. No Windows control change or blocked-DLL execution is performed. See [evidence/IR-14/run-20260923T021324976415Z/notes.md](evidence/IR-14/run-20260923T021324976415Z/notes.md). record_ir14.py derives the report from saved captures without HTTP and must not be rerun after recording. IR-15 remains unexecuted.

## IR-15 reproduction after explicit case authorization

```powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir15.py
```

The existing run has already executed; no requests were repeated to finish its review. A new invocation creates a new evidence directory and private seeded database, verifies the recorded original backup and makes a consistent snapshot before requests. It first attempts full-app import. The saved attempt was blocked by Windows Application Control while importing SciPy _batched_linalg, so it explicitly selected exact source-handler functions with the original schema/solution component and an audit retrieval observer. Ten 503 responses were deliberate stops with no ranking, not product behavior.

The declared limit is 19 target POSTs plus one login, one profile and GET /docs and /openapi.json (23 HTTP total). Groq must already be disabled, and no redirects are followed. Exact inputs and harmless source marker are saved in [evidence/IR-15/run-20260923T023805163543Z/inputs.json](evidence/IR-15/run-20260923T023805163543Z/inputs.json). Full result and scope: [evidence/IR-15/run-20260923T023805163543Z/notes.md](evidence/IR-15/run-20260923T023805163543Z/notes.md). The owned server is stopped. Saved Swagger/OpenAPI responses belong to the selected-handler app; they do not certify full-app startup or depict browser screenshots. Do not send these bodies to unrelated/public systems.

```powershell
.\.venv\Scripts\python.exe -B audit\scripts\record_ir15.py
```

The second command only generates the reviewed report from saved captures; it sends no HTTP. It is a one-time writer and must not be rerun after review.json exists. No dependency repair, OS policy workaround, bonus test or application mitigation has been executed.
