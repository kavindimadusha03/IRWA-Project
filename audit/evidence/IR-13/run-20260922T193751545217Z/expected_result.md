# IR-13 criteria fixed before execution

- Objective: access without login. Four targets only: GET /home, POST /tickets/create, POST /agents/retrieval/search, POST /agents/knowledge/analyze. One request each; no automatic redirect following.
- Expected policy: protected UI/ticket operations reject anonymous access or redirect to login; sensitive retrieval/knowledge-analysis operations reject anonymous callers. Current missing agent dependencies are a suspected weakness, not a public-access PASS rule.
- Use valid benign form and AgentMessage bodies; knowledge analyze takes no body. Request validation (422) is not authentication evidence. Fresh client per target, Cookie and Authorization absent on built requests, ambient auth/proxies disabled.
- Per-target PASS: login redirect or explicit 401/403 without protected data or mutation. Verify redirect is the actual login target (/ under this app); do not follow it.
- Per-target FAIL: valid anonymous request executes protected operation or returns internal source/analytics data. 200 alone is insufficient: inspect actual response and original function invocation. 422/5xx/environment failures are inconclusive unless separately sufficient evidence proves access.
- Overall PASS requires all four targets to satisfy intended policy. Any valid demonstrated exposure makes IR-13 FAIL, while other target outcomes remain separate.
- Verify original private backup; seed only synthetic original CSVs/users into fresh isolated SQLite DB, snapshot it before requests, own the loopback socket and verify all table counts/hashes after each request. No login or production-data use.
- Capture serialized nonsecret requests, absent-auth booleans, initial status/Location/body, actual function result and redacted logs. Never save credentials, cookies, tokens or raw account rows.
- Retrieval evidence should identify returned source IDs/text/type/status and match against actual eligible records. Knowledge-health evidence should distinguish aggregates from individual ticket text; do not claim clusters/examples unless actually returned.
- Record configured Groq and any original chat calls; authentication observations do not depend on successful LLM generation. Observe original functions without replacing scores or security checks.
- One common missing-authentication root cause may support one formal finding across agent routes. Explain impact/likelihood/severity under tested loopback/synthetic scope; do not infer internet reachability, real-user disclosure, privilege escalation or DoS.
- No role-switching, invalid-token, alternate endpoint, schema-abuse, credential-guessing, stress tests, repairs or authentication fixes. IR-14/IR-15 remain unexecuted.
