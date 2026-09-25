# IR-13 - Unauthenticated Access

**Reviewed result: FAIL.** A01/A02 correctly redirect anonymous UI/ticket requests. A03/A04 return internal retrieval and knowledge-health data without authentication. **VULN-IR13-01, Medium:** missing authentication on two sensitive agent APIs, confirmed on an isolated loopback instance with synthetic data. No authentication fix was applied.

- Test ID: IR-13
- Test Name: Unauthenticated Access
- Test Objective: Verify whether intended protected UI and sensitive agent operations reject requests without login.
- Component Being Tested: home(), create_ticket(), current_user_from_request(), retrieval_search(), knowledge_analyze(), search_knowledge(), analyze_knowledge_health(), app/router dependency wiring.
- Input / Attack Scenario: One GET /home; one valid POST /tickets/create form; one valid AgentMessage POST /agents/retrieval/search for My laptop is connected to Wi-Fi but there is no internet.; one bodyless POST /agents/knowledge/analyze. Fresh unauthenticated client per target; exact inputs saved.
- Preconditions: Owned loopback server, original synthetic corpus/users in isolated DB, actual source and working-DB hashes match baseline, original private backup and seeded snapshot verified. No cookies/authorization headers or prior login; no automatic redirect following.
- Steps: Predeclare four requests and policy; validate benign schemas; verify backup/isolation; start owned server and snapshot all tables; send one fresh-client request per target; capture initial status/Location/full body; verify table hashes after each; match exposed data to source and function returns; stop server and review.
- Expected Behaviour: Protected operations redirect to login or return 401/403 without protected data/mutation. Valid 200 internal agent results violate intended policy; source-level Public classification is not a secure-behavior exception.
- Actual Behaviour: /home and /tickets/create returned 303 to / with zero-byte bodies, no ticket created. Both agent APIs returned anonymous 200: retrieval 3284 bytes with four resolved histories plus one KB body; health 384 bytes with five category aggregate rows, clusters empty. No login/provider call, no persistent table changes; server stopped.
- Evidence: [notes.md](notes.md), A01-A04 request/response/database_after files, endpoint_results.json/CSV, disclosure_review.json, finding.json, original function results and review.json.
- Observation: Direct agent APIs omit authentication despite guarded UI routes. Request metadata is schema input, not identity. All returned source fields match seeded eligible records; knowledge cache is the only observed nonpersistent side effect.
- Outcome: FAIL overall; A01/A02 PASS and A03/A04 FAIL.
- Vulnerability Identified: YES - VULN-IR13-01, missing authentication on sensitive agent endpoints; one shared root cause covers both failures.
- Impact: Anonymous read access to synthetic internal source text and aggregate analytics demonstrated. Similar reachable deployment with sensitive data could expose it; no real-data breach, ticket mutation, credential disclosure or takeover observed.
- Likelihood: Easy for callers who can reach the service: one valid request, no identity or interaction. Tested once per route on localhost; internet reachability and population prevalence unmeasured.
- Severity: Medium, qualitative under the audit rubric; meaningful but limited demonstrated confidentiality/control weakness. No High/Critical or numeric CVSS claim.
- Technical Explanation: get_session() supplies DB access only. Agent handlers/router and FastAPI inclusion add no verified-user guard; UI handlers explicitly use current_user_from_request(). Anonymous HTTP results exactly match original agent function outputs.
- Recommended Mitigation: After approval, apply shared verified identity and explicit route/role/service permissions before sensitive agent invocation; add absent/invalid credential regression tests and restrict returned data to authorized needs. No fix applied.
- Conclusion: Local runtime confirms missing authentication and data return from two agent APIs while UI denial holds. Register one Medium finding. IR-14 and IR-15 remain unexecuted.
- Testing Limitations: Four requests on an owned localhost server; original synthetic corpus; no real users/public systems, authenticated role testing, token attacks, write exploitation, DoS or deployment/proxy assurance. Groq disabled and unused.

## Intended policy, scope and valid preconditions

The audit plan expects protected UI/ticket actions and sensitive internal agent operations to reject anonymous callers. Baseline endpoint_inventory.md classified the agent handlers as Public because that accurately described their source code. It was not a declaration that unrestricted internal-data access meets the intended security policy. This run validates the suspected gap rather than redefining a 200 response as secure.

Exactly four target requests were sent, one per declared route. Each used a newly constructed httpx client with trust_env=False and follow_redirects=False. Built requests had no Cookie, Authorization or Proxy-Authorization header; every cookie jar was empty before and after its request. No login, forged identity, invalid-token test, automatic redirect, extra health request or other target was used. The input sender audit_client is an ordinary declared string, not an impersonated privileged account.

The server bound its own 127.0.0.1 socket before startup; therefore the requests could not accidentally target another instance. Actual base URL: http://127.0.0.1:8001. The original FastAPI app/routes/functions executed without access-rule, score, dependency or response substitutions. Wrappers around the two agent functions only count/capture unchanged original returns. The owned server.started flag established startup before requests; all four actual HTTP responses establish runtime availability.

A temporary SQLite database contained only original project synthetic CSVs and four seeded accounts; no working-database rows were copied. Counts before requests: 80 articles, 500 historical tickets and four users. All four roles were present, but no role logged in. Original source/main-database hashes and the original private Phase1 backup were verified. After app startup, a separate private SQLite snapshot was made before the first request; integrity_check=ok and all ten table states matched. Its hash is `07f8ea803942e2ab076d2bc128c65a71b2769294368251c82917a0fe680c7963`; private path/method are recorded in isolated_database_backup.json.

Valid form minimum lengths and the AgentMessage model were checked before requests. The knowledge-analysis endpoint declares no request body. Thus the observed behavior is not the result of deliberately malformed inputs, and no 422 schema failure is interpreted as authentication. Actual retrieval fields match the 427 eligible source records from the original CSVs.

## Exact requests and initial responses

| ID | Method / endpoint | Authentication sent | Initial response | Body bytes | Outcome |
|---|---|---|---|---:|---|
| A01 | GET /home | None | 303 Location: / | 0 | PASS |
| A02 | POST /tickets/create | None | 303 Location: / | 0 | PASS |
| A03 | POST /agents/retrieval/search | None | 200 | 3284 | FAIL |
| A04 | POST /agents/knowledge/analyze | None | 200 | 384 | FAIL |

A01: `GET /home`, no body. A02: `POST /tickets/create`, application/x-www-form-urlencoded with the following decoded fields:

~~~json
{
  "title": "No-login ticket audit",
  "description": "My laptop is connected to Wi-Fi but there is no internet."
}
~~~

Both return 303 Location `/`, the login-page route in this app. Neither redirect is followed; both actual response bodies are empty, with no Set-Cookie header. Ten table fingerprints remain identical after each request. Ticket count remains 500, ticket row hash is unchanged and no agent log/citation/notification was created. These two checks PASS anonymous denial; they do not establish authenticated role or ownership behavior.

A03: `POST /agents/retrieval/search`, application/json:

~~~json
{
  "message_id": "ir13-retrieval-001",
  "request_id": "ir13-local-audit",
  "sender": "audit_client",
  "receiver": "retrieval_agent",
  "task": "retrieve_knowledge",
  "payload": {
    "issue": "My laptop is connected to Wi-Fi but there is no internet."
  }
}
~~~

A04: `POST /agents/knowledge/analyze`, no body. A03 and A04 return application/json, status200 and no Location/Set-Cookie headers. Both original agent functions execute exactly once; HTTP JSON equals their captured original function results. There are zero redirect-history entries for all responses. A03 returns 3284 bytes and A04 returns 384 bytes. A01-A04/request.json preserve serialized bodies and actual header-absence checks; response.json preserves exact body_text plus its SHA256 and parsed JSON. response_body.txt is a convenient text copy with a final newline.

## Retrieval disclosure actually observed

A03 returns decision HIGH, best_score 0.9441488884601732, and five full result items. Its success is an authentication failure regardless of ranking quality. This test does not re-score retrieval accuracy or generate a recommended answer.

| Source | Type | Status | Score |
|---|---|---|---:|
| SYN-0138 | resolved_ticket | resolved | 0.9441488885 |
| SYN-0033 | resolved_ticket | resolved | 0.8157104251 |
| KB-001 | Internal KB | approved | 0.7957807086 |
| SYN-0037 | resolved_ticket | resolved | 0.7257433700 |
| SYN-0027 | resolved_ticket | resolved | 0.6665125288 |

All seven original source fields in each result exactly match the seeded eligible record. The returned content below is synthetic audit evidence; no troubleshooting step was performed.

### SYN-0138 - Laptop connected to Wi-Fi but no internet access

~~~text
Problem: Laptop connected to Wi-Fi but no internet access on macOS. It happens on my work laptop.
Root cause: 
Resolution: Restarted the network adapter and flushed the DNS cache.
~~~

### SYN-0033 - Wi-Fi connected but browser says no internet

~~~text
Problem: Wi-Fi connected but browser says no internet on Windows 11. I already restarted the device once.
Root cause: 
Resolution: Restarted the network adapter and flushed the DNS cache.
~~~

### KB-001 - DNS Cache Recovery - Guide 1

~~~text
If Wi-Fi is connected but internet access is unavailable, open Command Prompt and run ipconfig /flushdns. Reconnect to Wi-Fi and test again.
~~~

### SYN-0037 - Internet unavailable although Wi-Fi is connected

~~~text
Problem: Internet unavailable although Wi-Fi is connected on Ubuntu. The issue happens repeatedly.
Root cause: 
Resolution: Restarted the network adapter and flushed the DNS cache.
~~~

### SYN-0027 - Wireless icon shows connected but websites do not load

~~~text
Problem: Wireless icon shows connected but websites do not load on Windows 10. The issue happens repeatedly.
Root cause: 
Resolution: Restarted the network adapter and flushed the DNS cache.
~~~

Observed disclosure: four historical problem descriptions and resolution notes, one approved internal KB body, titles/IDs/category/status/type/OS and ranking values. Historical Root cause labels are present but their values are empty; no nonempty root-cause details were demonstrated. The seeded articles have security_class=internal in the corpus metadata; that security_class field itself is not in this HTTP response. No credentials, owner identity, account profile, draft article, unresolved-ticket text or real-user data was returned in this request. The finding concerns unauthenticated access to this internal application data under the declared policy.

## Knowledge-health disclosure actually observed

A04 returns the following five rows plus `clusters: []`:

| Category | Tickets | Coverage | Gap |
|---|---:|---:|---|
| Software Installation | 68 | 0.206 | GAP |
| Outlook / MFA | 67 | 0.209 | GAP |
| Windows / Updates | 66 | 0.212 | GAP |
| Remote Desktop | 65 | 0.215 | GAP |
| VPN | 64 | 0.219 | GAP |

These are internal aggregate counts and knowledge-health indicators. With 500 seeded tickets, original analyze_knowledge_health() uses its >60 count-based coverage calculation and skips clustering at >=120. It does not expose individual ticket examples in this response. The health cache was absent before the request and present afterward: original analysis ran and populated only a process-local cache. No cached authenticated-session result was seeded into the test. Source code has other dataset-size paths; their possible outputs are not claimed as observed disclosures here.

## Technical cause and finding

**VULN-IR13-01 - Missing authentication exposes internal agent retrieval and knowledge analytics.**

The protected handlers call current_user_from_request(), which reads the access_token cookie and returns no user when absent. home() and create_ticket() then redirect to `/`. In contrast, retrieval_search() accepts AgentMessage plus get_session(); knowledge_analyze() accepts only get_session(). That dependency opens a database session and performs no identity check. Agent router creation and app.include_router(agents.router) add no authentication guard, and runtime metadata records zero app-router global dependencies and zero user middleware. Handler source excerpts/dependencies are in route_preflight.json.

AgentMessage validates five string metadata fields and a payload dictionary; none proves sender identity. In this ordinary request no privileged sender spoofing was required. The two sensitive handlers invoke search_knowledge()/analyze_knowledge_health() and return their complete results to the anonymous client. Front-end redirects therefore do not protect direct agent API operations. This is a demonstrated missing guard under intended policy, not merely an inference from a Public inventory label.

Source references: [agents.py](../../../../app/routes/agents.py) retrieval route lines24-26 and knowledge route38-40; [main.py](../../../../app/main.py) FastAPI construction20, router inclusion28 and home guard46; [auth.py](../../../../app/routes/auth.py) current_user_from_request26; [tickets.py](../../../../app/routes/tickets.py) create_ticket29; [database.py](../../../../app/database.py) get_session; [knowledge_intelligence_agent.py](../../../../app/agents/knowledge_intelligence_agent.py) analyze_knowledge_health. Line references describe the preserved original source, not a patch.

**Impact:** anonymous read access to the shown source content and internal aggregate analytics is demonstrated. Similar deployment with sensitive data, reachable by untrusted callers, could expose that data. No real-user disclosure, credential leak, account takeover, modification, denial of service or broad corpus extraction was tested or observed.

**Likelihood:** straightforward for a caller able to reach the service: a normal valid request needs no credential or user interaction. Each route was tested once; this establishes the local behavior, not an empirical population probability. The audit server listened only on loopback; external network reachability, deployment firewall/proxy controls and production exposure are untested.

**Severity/risk: Medium**, qualitative under the audit rubric. This is a meaningful authentication/confidentiality failure with easy invocation for a reachable caller, while demonstrated exposure is limited and all test data is synthetic. Higher severity, public exposure, real harm or a numeric CVSS score would require further evidence. One finding covers the common missing-authentication cause across two APIs; UI successes remain separate.

**Recommended mitigation, not applied:** require a shared verified active-user or authenticated service identity before invoking sensitive agent functions, then enforce explicit role/service permissions for each operation. Limit knowledge-health analysis to intended analysts/services and scope returned content to authorized needs. Reject absent/invalid credentials before expensive/data-reading work. Add authenticated-positive and missing/invalid-credential regression checks during authorized remediation. Do not treat payload sender strings, CORS, hidden UI links or an assumed external gateway as authentication. Role matrix and token probes are not performed in this case.

**Status:** confirmed locally; open; remediation not applied. Intended policy, reproduction, scope and severity are retained in finding.json and the vulnerability register. No application source, JWT setting, role or authentication configuration was changed.

## Integrity, runtime and limits

database_preflight.json and each A01-A04/database_after.json record only row counts and per-table hashes, not credential-bearing database rows. All ten table states match before/after each request. Final counts are unchanged: 80 articles, 500 tickets, four users; agentlog,category,notification,passwordresettoken,securityevent,solutionfeedback,ticketcitation remain empty. Seeded database main file and private snapshot are unchanged. Main application database and all baseline source files match original hashes; earlier audit evidence remains preserved. Main-file checks do not cover unrelated concurrent WAL writes by another instance.

Worker start 2026-09-22T19:37:52.404153+00:00; finish 2026-09-22T19:38:17.447684+00:00 UTC. Parent elapsed 27.689 seconds, exit 0, no timeout. Original retrieval function took 3.162 seconds; original knowledge analysis took 0.026 seconds. The recorded get_model() call took 0.442 seconds, excluding prior import/startup time. Server stopped after capture.

Configuration retained BM25 0.45 / semantic 0.55, HIGH 0.68 / UNCERTAIN 0.55, cached all-MiniLM-L6-v2 and one numerical-library thread. Groq was disabled and no chat call occurred. Authentication findings do not depend on LLM availability or answer generation.

Limits: four declared requests only; original synthetic CSV corpus; local development, no enterprise/public/production system or real users; no authenticated positive control in this case, alternate agent endpoint, role bypass, malformed credentials, ownership test, source poisoning, schema abuse, stress/load or DoS testing. Redirect destination is identified from preserved app source; redirects were deliberately not followed. HTTP JSON/text is actual response evidence, not a fabricated screenshot.

## Evidence and reproduction

| Files | Purpose |
|---|---|
| inputs.json, expected_result.md | Exact request bodies, target limit and intended policy fixed before execution |
| preconditions.json, corpus_preflight.json, eligible_records.json | Baseline source/main-DB/backup checks and actual synthetic retrieval corpus |
| route_preflight.json | Actual original handler source/dependency/body metadata |
| isolated_database_backup.json, database_preflight.json | Private consistent snapshot and nonsecret table fingerprints before requests |
| A01-A04/request.json | Actual built bodies, absent-auth checks, fresh-client and redirect settings |
| A01-A04/response.json, response_body.txt | Initial status/Location/body, byte count and original-body hash |
| A01-A04/database_after.json, database_postflight.json | No ticket/persistent-table changes after each request and final snapshot check |
| retrieval_function_result.json, knowledge_function_result.json | Original function outputs and health-cache state |
| response_summary.json, execution.json, process_result.json, terminal_log.txt | Raw request counts, responses, timing, shutdown and integrity |
| endpoint_results.json/CSV, disclosure_review.json, finding.json, review.json, evidence_integrity.json, notes.md | Later reviewed outcomes and confirmed scoped vulnerability |

Already executed once. This command creates a new synthetic database/evidence run, snapshots it, sends only the four requests and stops its server:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir13.py
~~~

The completed run used http://127.0.0.1:8001; that audit server is now stopped. Use the runner to reproduce its isolation instead of sending mutation requests to an unrelated localhost instance. Exact method/URL/body are saved per target. No credentials are required or included in these test requests.

**Conclusion:** IR-13 FAIL; two UI checks PASS and two anonymous agent-data responses FAIL. VULN-IR13-01 is confirmed at Medium severity within the local synthetic scope. Original capture statuses remain Unassessed for preservation; review.json provides the later verdict. IR-14 and IR-15 remain unexecuted; stop before IR-14.
