# Phase 1 baseline: actual observations

Phase 1 preparation and baseline attempts are recorded. The baseline is **not ready for security-test interpretation**: Windows memory failures prevented retrieval evaluation, login verification and known-query verification. No metric or success is invented.

Environment captured at 2026-09-21T17:39:32.353223+00:00. Evidence timestamps are UTC.

## System configuration

| Setting | Observed value | Evidence |
|---|---|---|
| Python | 3.12.10 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| FastAPI | 0.115.6 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| SQLModel | 0.0.22 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| sentence-transformers | 3.3.1 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| rank_bm25 (distribution rank-bm25) | 0.2.2 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| pytest | 9.1.1 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Uvicorn | 0.34.0 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Operating system | Windows-11-10.0.26200-SP0 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Database type | SQLite | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Embedding model | all-MiniLM-L6-v2 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Configured LLM model | llama-3.1-8b-instant | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Normal localhost URL | http://127.0.0.1:8000 | evidence/baseline/environment.json or low_memory/application_baseline.json |
| Isolated baseline URL | http://127.0.0.1:8001 | evidence/baseline/environment.json or low_memory/application_baseline.json |

SECRET_KEY and GROQ_API_KEY entries exist. Values are not recorded. The test process reported llm.enabled=false; model name is configuration, not proof of a successful provider request.

## Retrieval configuration

| Setting | Current Value | File |
|---|---|---|
| BM25 tokenization | Lowercase; regex technical/hex tokens; selected punctuation preserved; slash components | app/services/bm25.py:7-47 |
| Query preprocessing | Phrase/abbreviation/typo replacements, filler removal, fuzzy cutoff 0.72, repeated-token removal | app/services/hybrid_search.py:97-153 |
| Embedding model | all-MiniLM-L6-v2 | app/services/embeddings.py:11 |
| Hybrid BM25 weight | 0.45 (effective value) | app/config.py:16 |
| Hybrid semantic weight | 0.55 (effective value) | app/config.py:17 |
| HIGH threshold | >= 0.68 (effective value) | app/config.py:18; retrieval_agent.py:113 |
| UNCERTAIN threshold | >= 0.55 and below HIGH (effective value) | app/config.py:19; retrieval_agent.py:115 |
| top-k | Ticket/direct retrieval 5; chat 3; recommendation uses first 3 sources | coordinator.py:54; retrieval_agent.py:92; chat.py:60; solution_agent.py:30 |
| Source trust weights | Draft 0; approved or internal_kb 1; resolved or resolved_ticket 0.85; other 0.7, in that branch order | app/agents/retrieval_agent.py:43-53 |
| Exact error-code boost | +0.35 for matching hexadecimal code | app/services/hybrid_search.py:222-230 |
| Metadata eligibility | Approved KB; RESOLVED tickets with nonblank resolution; no per-user/security-class filter | app/agents/retrieval_agent.py:56-89 |
| Metadata ranking | Category +0.18; selected OS +0.14 to +0.18; approved/resolved +0.08; shortlist boosts, not hard category/OS filters | app/agents/retrieval_agent.py:17-40,94-110 |
| Duplicate handling | First normalized title/content match retained; same-category content Jaccard >=0.9 removed | app/services/hybrid_search.py:162-201 |
| Model/document cache | Model maxsize=1; whole ordered corpus tuples maxsize=128; query re-encoded | app/services/embeddings.py:9-44 |

Settings above came from effective nonsecret configuration inspection plus fixed source parameters. Scores can exceed 1 and are not probabilities. No parameter was retuned.

## Database and accounts

knowgap.db exists and was opened using a read-only SQLite URI with uri=True and PRAGMA query_only=ON. No rows were edited.

Tables: agentlog, category, knowledgearticle, notification, passwordresettoken, securityevent, solutionfeedback, ticket, ticketcitation, user.

| Table | Existing database count |
|---|---|
| user | 21 |
| ticket | 528 |
| knowledgearticle | 81 |

| Role | Active accounts |
|---|---|
| ADMIN | 1 |
| CUSTOMER | 18 |
| IT_SUPPORT | 1 |
| KNOWLEDGE_ANALYST | 1 |

All four required roles exist. Role presence does not prove login succeeds. No existing usernames, hashes or passwords are included.

Private backup created with sqlite3.Connection.backup(); integrity_check returned ok. Its location and SHA-256 are recorded in evidence/baseline/database_backup.json. Keep the actual backup outside Git and report submissions.

CSV counts: 80 KB articles, 500 historical tickets and 21 gold queries. The existing database has 81 KB articles and 528 tickets. Runtime baseline fixtures use the CSV data only.

## Actual automated-test result

- Result: 5 failed, 9 passed, 405 warnings in 16.83s.
- Exit code: 1. Total helper duration: 18.299 seconds.
- Existing test source was unchanged; the configured application database was replaced only inside the test process with a temporary SQLite file.
- Pytest cache output was disabled. Model loading used the existing local cache.
- Evidence: evidence/baseline/pytest_output.txt and pytest_result.json.
- All five failures reached model loading and raised Windows OSError 1455: The paging file is too small for this operation to complete.
- This is an environment/reliability blocker, not five demonstrated security vulnerabilities. Failed embedding tests do not establish incorrect ranking behavior.

Failed test names:

- tests/test_ai_improvements.py::test_document_embeddings_are_cached_for_repeated_queries
- tests/test_ai_improvements.py::test_metadata_reranking_prefers_windows_11_vpn_article
- tests/test_ai_improvements.py::test_search_knowledge_exposes_score_breakdown_and_source_metadata
- tests/test_ai_improvements.py::test_hybrid_rank_gives_exact_error_code_bonus
- tests/test_ai_improvements.py::test_hybrid_rank_deduplicates_near_duplicate_articles

LLM observation: configured_enabled=False; attempts=2; successful chat returns=0; error types=['RuntimeError', 'RuntimeError']. Exceptions exercised the application's fallback. A successful chat return would not alone prove valid JSON parsing or answer adoption.

## Actual IR evaluation attempt

Initial attempt exited with native OpenBLAS memory-allocation errors before metrics. A separate one-thread retry also exited 1 with Windows paging-file error 1455 while loading MiniLM. Neither attempt produced numeric metrics.

| Method | P@1 | P@5 | Recall@5 | MRR | Other metrics |
|---|---|---|---|---|---|
| BM25 | Unavailable | Unavailable | Unavailable | Unavailable | Hit Rate/nDCG not implemented |
| Semantic | Unavailable | Unavailable | Unavailable | Unavailable | Hit Rate/nDCG not implemented |
| Hybrid | Unavailable | Unavailable | Unavailable | Unavailable | Hit Rate/nDCG not implemented |

Unavailable means no score was produced; it does not mean zero accuracy.

Evidence: initial_evaluation_native_failure.json; low_memory/ir_evaluation_output.txt, ir_evaluation_result.json and evaluation_process_result.json.

Metric meanings: P@1 is first-result relevance; P@5 is relevant hits among five divided by five; Recall@5 is relevant hits divided by the labelled relevant set; MRR averages reciprocal rank of the first relevant result across the full ranking.

The evaluator uses approved CSV articles, raw query scoring and fixed BM25/semantic weights 0.45/0.55. There is no weight sweep. It omits the application's normalization, deduplication, exact-code bonus, trust/metadata adjustments, historical tickets and confidence decisions. Even its BM25 branch computes semantic scores. Duplicate labels can omit equivalent answers, and an empty relevance set receives zeros without assessing abstention.

## Application startup, login and known-query evidence

Bound only to http://127.0.0.1:8001 using a reserved socket. Port 8000 was occupied, so the audit used 8001 without interacting with the existing server. Database fixtures were synthetic and separate.

| Baseline check | Actual observation | Interpretation |
|---|---|---|
| Startup /health | {"passed": true, "http_status": 200} | Observed positive check passed |
| Swagger /docs | {"http_status": 200, "passed": true} | Observed positive check passed |
| Synthetic registration | {"http_status": 500, "passed": false} | Did not meet baseline expectation |
| Valid login | No completed result recorded | Unverified; baseline stopped before completion |
| Known Wi-Fi retrieval | No completed result recorded | Unverified; baseline stopped before completion |
| Ticket workflow | No completed result recorded | Unverified; baseline stopped before completion |

Registration's HTTP 500 is linked in application_output.txt to argon2.exceptions.HashingError: Memory allocation error. The subsequent request failed with a connection ReadError; no successful login is claimed. Known retrieval and ticket creation were not reached in this baseline run.

Expected normal query (fixed before execution): My laptop is connected to Wi-Fi, but websites do not load and there is no internet access. Expected evidence: a relevant approved Wi-Fi guide. This expected result is not an observed result.

Audit server stopped: True. Evidence: low_memory/application_baseline.json, application_output.txt and smoke_process_result.json. No browser screenshot was captured.

## Integrity and readiness

Completed collection actions recorded unchanged application/data/evaluation/test source hashes and unchanged original knowgap.db main-file hashes. The helper never opens that original file for writes. Checksums do not cover concurrent WAL changes by the user's separate running instance.

- Source/configuration, endpoint/component inventories, database tables/roles, backup and test preparation: recorded.
- Existing test run: completed with real failures preserved.
- IR evaluation: attempted twice; unavailable due memory exhaustion.
- Startup and Swagger: observed working on the isolated instance.
- Login and known retrieval: not established.
- Groq generation: unavailable in the loaded configuration; fallback only.
- IR-01 through IR-15: Not run; no attack executed.

Resolve memory availability before drawing retrieval/security conclusions from new executions. Do not lower password-hashing settings, replace embeddings or modify ranking to hide this baseline. Preserve these logs when recording a later successful baseline.

Source-review concerns in endpoint_inventory.md and component_inventory.md remain candidates for later tests. No vulnerability severity is assigned merely because these baseline checks failed.
