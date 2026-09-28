# IRWA Student 4 — fresh IR-01–IR-15 regression and evidence kit

This kit was prepared **from the current `IRWA-Project.zip`**. It moves adapted reusable tests outside `audit/` so you can archive the *old evidence* and run the cases against **your updated system**. It is not a copy of the old audit outcomes, and it makes no claim that previously reported failures still exist.

**Nothing in this kit deletes, edits, or seeds your main `knowgap.db`.** The original full-evidence runners fingerprint the working database and work with separate, temporary synthetic databases. The kit contains no `.env`, real database, prior audit results, Git history or downloaded models.

## 1 — Install the kit into YOUR existing project

Open PowerShell **inside the project root**—the folder with `app/`, `data/`, `requirements.txt`, and `knowgap.db`. Download `IRWA_IR_Retest_Kit.zip` into this folder and run:

```powershell
Expand-Archive -Path .\IRWA_IR_Retest_Kit.zip -DestinationPath . -Force
py irwa_retest\self_check.py
```

You should see `irwa_retest/` beside `app/`, **not** inside `audit/`. The self-check is standard-library-only and never runs the app or changes your data. Read the instructions below before removing the old audit.

## 2 — Archive the previous audit before regenerating it

Because your old results were collected **before your system update**, retain them outside the repository to document what changed. If you have already copied the old audit elsewhere you can omit this step.

```powershell
# From your project root (adjust the destination if you already have that folder):
New-Item -ItemType Directory -Force ..\IRWA_Audit_Backups
Move-Item -Path .\audit -Destination ..\IRWA_Audit_Backups\audit_before_retest
```

If the destination already exists, choose a new name. The complete original `audit/`, including its results and old scripts, will be in `..\IRWA_Audit_Backups\audit_before_retest`. The kit is **outside** `audit/`, so it survives the move.

For another manual backup, copy the complete project before starting. Close any server or editor processes using `knowgap.db`; if the app uses SQLite WAL mode, the full project backup must include any `knowgap.db-wal` and `knowgap.db-shm` sidecars too. Don't publish `.env`, database copies, authorization cookies or secret-bearing logs in your report/Git repository.

## 3 — Prepare your existing Python environment

Use **your project’s existing virtual environment** if the updated app already runs. These examples create one only if it is missing:

```powershell
if (!(Test-Path .\.venv\Scripts\python.exe)) { py -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install pytest
```

These imports follow your *current* `requirements.txt`. The original full ranking experiments additionally need **the real cached** `sentence-transformers/all-MiniLM-L6-v2` model. They set Hugging Face to **offline mode**, deliberately preventing an accidental download or model substitution. If your original experiments ran on another computer or Windows account, cache the same model locally using an approved normal setup first; then rerun.

## 4 — Run the regenerated tests

```powershell
# Inspect all 15 cases and dependencies.
.\.venv\Scripts\python.exe irwa_retest\run_all.py --list

# Quick regression checks first (synthetic, in-memory DB, no API or model download):
.\.venv\Scripts\python.exe irwa_retest\run_all.py --quick

# See all planned full steps without executing them:
.\.venv\Scripts\python.exe irwa_retest\run_all.py --all --dry-run

# Collect fresh baseline + existing tests + IR evaluation + all 15 original IR flows:
.\.venv\Scripts\python.exe irwa_retest\run_all.py --full
```

Or run quick and full together from a completely archived/empty audit:

```powershell
.\.venv\Scripts\python.exe irwa_retest\run_all.py --all
```

`--full` refuses to start if **any old baseline or IR case directory** remains under `audit/evidence`. It does **not** delete it. The full runners execute `IR-01` first because many following cases depend on it; the suite reuses only the **latest current** evidence from prerequisite cases rather than date-pinned September folders.

After a fresh baseline and prerequisite cases exist, rerun just one case, for example:

```powershell
.\.venv\Scripts\python.exe irwa_retest\run_all.py --case IR-13
```

Most tests run in **provider-disabled** mode (`GROQ_API_KEY` blanked in child processes). This is intentional for repeatable retrieval/security comparisons without sending synthetic tickets to a live provider. Keep the **same provider mode for every run**. The optional `--allow-live-llm` flag can incur usage or transmit prompts and **does not work for IR-15**, which explicitly requires an offline provider; do not use it for a complete all-case retest.

For IR-14 only, `--route-harness` is an explicit reduced-scope fallback when full app import is blocked; a router-only test is **not** proof about the deployed full application. IR-15 also records whether it uses a full-app run or a clearly labelled reduced-scope handler harness.

## 5 — Find your evidence, then make your own PASS/FAIL assessment

The launcher creates:

```text
audit/
  evidence/
    baseline/                      # current source/environment baseline and protected DB backup
    IR-01/run-<UTC timestamp>/      # requests, responses, trace and expected criteria
    IR-02/run-<UTC timestamp>/
    ...
    IR-15/run-<UTC timestamp>/
    retest_suite/run-<UTC timestamp>/
      suite_results.json          # execution completed / errors / blocked
      suite_summary.md            # convenient execution table
      *.log                       # subprocess outputs
```

**Execution success is not the same as passing a test.** Review the actual response, source ranking/citations, `expected_result.md`, and original `process_result.json` for each case. An exception, skipped prerequisite, missing embedding cache, or reduced-scope harness is **Inconclusive** for anything it did not assess; historical vulnerabilities are not automatically present after the update. Keep a dated old-vs-new comparison with evidence paths in your individual report. Fill in `irwa_retest/docs/fresh_result_template.md` as you assess the new run.

The original project also contains `tests/test_ai_improvements.py`, `tests/test_knowledge_health_performance.py`, `tests/test_retrieval_security_verification.py`, and `evaluation/evaluate_ir.py`; `--full` runs their existing baseline workflows. The new `quick_tests/` contains one focused test for each IR-01–IR-15 topic (with parameterized IR-08 format cases); **it is complementary, not a replacement for the original end-to-end evidence collection**. Some quick tests intentionally assert desired security or ranking behavior: if the changed system violates it, the test **should fail** and you should investigate rather than edit the expected result to force green.

## Troubleshooting

- **“Existing audit case/baseline folders found”:** Archive/move the **entire old audit** out of the project, not just the baseline JSON. Do not mix pre-update and post-update evidence.
- **“knowgap.db missing”:** Run `--quick` if you just want isolated checks. Full runners require the main file **read-only for integrity comparison/backup** even though they execute against temporary databases. Keep a full backup first.
- **`ModuleNotFoundError` or PyTorch/DLL/import errors:** Activate the virtual environment that runs the updated app; install its current requirements. Review the generated case error and distinguish environment failure from a genuine application regression.
- **Offline embedding cache missing:** The full IR tests deliberately stop rather than fetch a new model or silently switch models. The quick suite stubs *only the semantic-score calculation* to test the current BM25/routing logic.
- **A full case fails:** Check `audit/evidence/IR-NN/run-*/terminal_log.txt`, `execution.json`, `process_result.json`, then `audit/evidence/retest_suite/run-*/IR-NN.log`. The launcher continues with other independent cases; don't interpret a failed setup as a vulnerability.
- **Security tests after system update:** Current agent endpoints use verified login and role checks, so record **new actual HTTP status codes**. Do not reuse an older report's “unauthorized access” or “forged provenance” conclusion without fresh evidence.

## Scope, ethics and data safety

Run against **your own local copy** of the class project on `127.0.0.1`, using only seeded/demo accounts, bounded inputs and synthetic fixtures. These tests do not attempt privilege escalation against live systems or external targets. They never intentionally alter the working application files or live database. They do create new `audit/evidence` files. To share evidence for assessment, first review/sanitize it and follow your course requirements. If storing `audit/evidence` in Git, exclude DB backups, credentials and other private runtime details.
