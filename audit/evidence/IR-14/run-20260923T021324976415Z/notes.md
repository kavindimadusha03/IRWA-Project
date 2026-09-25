# IR-14 - Unauthorized Role Access

**Status: Partially assessed. All 15 original-router HTTP role checks PASS. Full-application verification is Blocked / Inconclusive. No new authorization vulnerability was demonstrated; VULN-IR13-01 remains open.**

## Runtime scope and preserved startup failure

The first attempt, [run-20260923T020808917231Z](../run-20260923T020808917231Z/process_result.json), failed while importing app.main. Windows Application Control returned WinError 4551 for torch_python.dll or a dependency. The stack passed through tickets/coordinator/retrieval/embeddings into PyTorch. No server started and zero login, profile or target requests were sent. This is an environment limitation, not an authorization FAIL. The original logs, inputs and integrity checks remain preserved.

The successful run was separately predeclared as a smaller HTTP integration test. An audit FastAPI app mounted the original auth, knowledge and admin routers, original static directory and original create_db_and_tables startup. Their handlers, SQLModel dependencies, templates, password verification, cookie issuance and role checks remained original. No dependency overrides, custom middleware or app-wide dependencies were installed. Source inspection of app/main.py confirms these routers have no additional registration-time guards. Identity observers called the original helper once per invocation and returned its unchanged user.

The harness does not load app.main or the retrieval stack and does not establish that the complete application currently starts. It does not load a substitute PyTorch module or change Windows policy, DLLs, installed packages or app source. Only the three declared privileged routes and login/profile controls were requested; redirect destinations were captured and not followed. Read [scope_adjustment.json](scope_adjustment.json), per-role runtime_mode.json and [full_application_attempt_review.json](full_application_attempt_review.json).

## Case record

- Test ID: IR-14
- Test Name: Unauthorized Role Access
- Test Objective: Verify that successful login grants only the stored role permissions and that submitted role/user_id fields cannot confer privileges.
- Component Being Tested: Original auth.login(), auth.profile_page(), auth.current_user_from_request(), knowledge.approve_article(), admin._admin_user(), admin.admin_page(), admin._ensure_categories() and admin.create_category(); SQLModel persistence and original templates.
- Input / Attack Scenario: CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, ADMIN and active unsupported AUDIT_VIEWER each send one POST /knowledge/81/approve, GET /admin and POST /admin/categories/create. Twelve denied-role attempts include claimed privileged role and another user_id in form/query fields; positive controls use normal fields. Draft AUDIT-IR14-DRAFT-001 and category IR14 Audit Category are synthetic fixtures.
- Preconditions: Original source/main database and private Phase 1 backup verified. Fresh seeded private database and pre-request snapshot per role; 80 original articles plus one draft, 500 tickets, four seed accounts (five only in unsupported-role worker). Normal login 303 /home, issued cookie present and authenticated profile 200 confirmed before every role sequence.
- Steps: Preserve failed full-app attempt; predeclare reduced scope; mount unchanged auth/knowledge/admin routers in isolated FastAPI HTTP harness; snapshot private database; login/profile control; submit three declared requests with redirects disabled; compare resolved identity and all table states after each; verify nonfixture articles and snapshots; stop owned servers; review saved evidence.
- Expected Behaviour: Only KNOWLEDGE_ANALYST approves the draft; only ADMIN views administration and creates the category. Other roles receive 403 without data or database changes. Permitted actions have only their declared effects, including original category initialization on ADMIN GET.
- Actual Behaviour: Full app import stopped with WinError 4551 on torch_python.dll before any HTTP. Separate original-router harness executed 25 HTTP requests, including all 15 role checks. Twelve denied cases returned 403, retained the logged-in identity and made no table changes. Analyst approval returned 303 /knowledge, changed only draft status/authoritative/updated_at. ADMIN GET returned 200 and created eight defaults; ADMIN category POST returned 303 and added exactly one category. All servers stopped.
- Evidence: [notes.md](notes.md), role_matrix.json/CSV, authorization_review.json, full_application_attempt_review.json, review.json, per-role login/profile/preflight/snapshot/postflight files and R01-R03 request/response/identity/before/after captures.
- Observation: The handlers use the stored database role resolved from authenticated token subject; ordinary request claims did not replace identity. ADMIN has no knowledge-approval override. AUDIT_VIEWER login succeeded but all three privileged operations were denied. GET /admin has a recorded category-initialization side effect.
- Outcome: Partially assessed overall: PASS for all 15 original-router HTTP checks; full-application verification Blocked / Inconclusive. Startup failure is not an authorization FAIL.
- Vulnerability Identified: No new vulnerability demonstrated in the tested role guards. VULN-IR13-01 remains confirmed Medium and open; this case neither fixes nor retests its agent endpoints.
- Impact: No unauthorized privileged data or persistent mutation observed in these checks. Authorized changes were confined to temporary fixture/article and category tables.
- Likelihood: No bypass demonstrated; prevalence or exploit likelihood cannot be inferred from this bounded passing sample.
- Severity: Not applicable for passing role checks. The environment blocker is not classified as an authorization vulnerability.
- Technical Explanation: current_user_from_request() verifies the issued token and loads User by sub. approve_article() requires KNOWLEDGE_ANALYST; _admin_user() requires ADMIN before admin data/mutation. Extra form/query role/user_id values do not participate in these checks. The harness retains original APIRoutes and dependencies with no overrides; identity observation calls the original helper and returns its result unchanged.
- Recommended Mitigation: No role-guard repair supported by this case. Retain explicit per-operation checks and these positive/negative controls. Complete a full-app rerun when the legitimate environment can load its dependencies; no Windows policy, DLL, dependency or application changes were made. The separate IR-13 remediation remains pending.
- Conclusion: Correct role enforcement observed across five active roles and three original routers, including field-claim attempts. Full-app startup/integration remains unverified. Stop before IR-15.
- Testing Limitations: Local synthetic dataset, original-router HTTP harness only, five active roles and three privileged endpoints. No JWT forgery, expiry/revocation, inactive-account, role-assignment API, object ownership, CSRF, alternative route, production, external or load tests. Redirects were not followed; no browser asset requests. Groq disabled and zero calls. Private main-file integrity checks do not cover unrelated concurrent WAL writes.

## Actual role matrix

| Authenticated stored role | POST /knowledge/81/approve | GET /admin | POST /admin/categories/create | Result |
|---|---|---|---|---|
| CUSTOMER | 403; no change | 403; no change | 403; no change | PASS |
| IT_SUPPORT | 403; no change | 403; no change | 403; no change | PASS |
| KNOWLEDGE_ANALYST | 303 /knowledge; fixture approved | 403; no change | 403; no change | PASS |
| ADMIN | 403; no change | 200; eight defaults added | 303 /admin success; one category added | PASS |
| AUDIT_VIEWER (unsupported fixture) | 403; no change | 403; no change | 403; no change | PASS |

All five normal login attempts returned 303 /home with an issued cookie; all five profile controls returned 200 and resolved the expected active user ID and stored role. Each target also resolved that same identity exactly once. These controls distinguish authenticated role denial from accidental unauthenticated rejection. Total traffic was 25 requests: five logins, five profiles and fifteen targets. The failed full-app attempt contributed zero requests. No automatic redirects, provider calls or browser asset requests occurred.

## Exact fixtures and request fields

Every role started in a new process/database with the original 80 synthetic articles, 500 tickets and four seed users. One draft fixture became article ID 81: doc_id AUDIT-IR14-DRAFT-001, title IR14 role approval fixture, category Printers, source_type internal_kb, status draft, authoritative false, supported_os Any, security_class internal, created_at/updated_at 2026-09-22T00:00:00. Its harmless content is: Synthetic audit note for testing knowledge approval. No troubleshooting action is requested. All complete fixture values are in [inputs.json](inputs.json).

Only the AUDIT_VIEWER database had a fifth active account provisioned directly as an isolated fixture. It used an existing synthetic credential privately; no credential or hash is included in the report. This demonstrates rejection of an authenticated unsupported role by the three guards; it does not show that a role-assignment API permits that role.

| Request | Allowed positive input | Denied-role claim added |
|---|---|---|
| R01 POST /knowledge/81/approve | No form body | Form role=KNOWLEDGE_ANALYST, user_id=3, status=approved, authoritative=true |
| R02 GET /admin | No query | Query role=ADMIN and user_id=4 |
| R03 POST /admin/categories/create | Form name=IR14 Audit Category, description=Synthetic category for role authorization check. | Same valid form plus role=ADMIN, user_id=4 |

Every request carried the normal cookie for its own logged-in account. Cookie presence is recorded, but values are omitted. No Authorization header, forged token, cookie substitution or stored-role change was used. Exact URL, encoded body and expected outcome are saved in each role/R01-R03/request.json. Across all 12 denied attempts, submitted role/user_id claims did not replace the observed identity.

## Responses and persistent effects

Every denied approval returned the 44-byte JSON body {"detail":"Knowledge Analyst role required"}; denied admin requests returned the 21-byte text Admin access required. All denied requests left all ten table counts and row hashes unchanged. There were no protected page bodies on denied admin requests.

KNOWLEDGE_ANALYST approval returned an empty 303 body with Location /knowledge. The only changed fixture fields were status (draft to approved), authoritative (false to true), and updated_at. Row count stayed 81. A separate digest, plus independent read-only comparison with the private snapshot, confirmed all other 80 articles were identical. Users, tickets, categories and all other tables were unchanged.

ADMIN GET /admin returned 200 with 21,584 bytes of actual admin HTML. The original _ensure_categories() added exactly eight active categories with empty descriptions: Accounts / Passwords, Outlook / MFA, Printers, Remote Desktop, Software Installation, VPN, Wi-Fi / DNS, Windows / Updates. This happened after the ADMIN guard; no denied caller triggered category initialization. The later create request returned empty 303 with Location /admin?message=Category+created. and added exactly the ninth category, matching the submitted name/description and active=true; the previous eight rows stayed identical. This observed GET side effect alone is not classified as a separate vulnerability, and no CSRF test was performed.

ADMIN could not approve the draft. CUSTOMER, IT_SUPPORT and AUDIT_VIEWER ended with every table unchanged, draft unapproved and zero categories. KNOWLEDGE_ANALYST ended with the one approved fixture and zero categories. ADMIN ended with an unapproved draft and nine categories. All original account rows and 500 ticket rows remained identical in every worker. The original working database was never a test target.

## Technical explanation

In [auth.py](../../../../app/routes/auth.py), current_user_from_request() decodes access_token, reads its sub and loads the database User. Normal login checks active state and password, then issues the cookie; profile_page() provides the authenticated control. The role here came from the loaded database record. In [knowledge.py](../../../../app/routes/knowledge.py), approve_article() checks user.role == KNOWLEDGE_ANALYST before loading and modifying the article. In [admin.py](../../../../app/routes/admin.py), _admin_user() requires ADMIN, and both admin_page() and create_category() reject other users before returning admin data or committing their changes. None of these guards reads the submitted role/user_id claim.

These exact checks explain the observed status and state matrix. They do not prove every route is protected: the separate VULN-IR13-01 missing-authentication finding remains confirmed Medium and open. The startup blocker is also distinct from access-control behavior.

## Evidence, integrity and reproduction

| Files | Purpose |
|---|---|
| inputs.json, expected_result.md, scope_adjustment.json | Criteria and explicit reduced runtime scope fixed before the harness requests |
| preconditions.json, process_result.json | Baseline source/database/backup, prior evidence and aggregate request/runtime checks |
| ROLE/inputs.json, route_preflight.json, runtime_mode.json | Exact fields, original handler source and harness construction |
| ROLE/login.json, profile_control.json/HTML | Actual login and authenticated profile control without credentials |
| ROLE/isolated_database_backup.json, database_preflight.json | Consistent private snapshot before login/targets and initial table/fixture states |
| ROLE/R01-R03/request.json, response.json, response_body.txt/HTML | Built nonsecret request, original status/Location/full response, byte length and hash |
| ROLE/R01-R03/resolved_identity.json, before.json, after.json | Stored identity and per-request all-table/fixture comparison |
| ROLE/postflight.json, execution.json, process_result.json, terminal_log.txt | Final state, zero LLM calls, shutdown and timings |
| role_matrix.json/CSV, authorization_review.json, review.json | Later reviewed per-request outcomes and explicit overall limits |
| full_application_attempt_review.json, evidence_integrity.json | Earlier startup failure classification and raw-evidence preservation |

Five private SQLite snapshots were made after fixture/setup and before login or test requests. Each passed integrity_check and matched all seeded table fingerprints; each snapshot hash still matches after testing. Raw databases remain outside the repository because they contain account credential hashes. Only nonsecret role metadata, fixture/category rows and table hashes are exported. The original Phase 1 private backup is also verified. Source hashes, original working-DB main-file hash, baseline and IR-01 through IR-13 evidence, and the failed full-app captures remain unchanged.

The harness run finished at 2026-09-23T02:13:53.536528+00:00 and took 28.276 seconds across five sequential workers. All worker exits were 0, without timeouts; all owned servers stopped. The same numerical-library thread settings, scoring configuration and disabled Groq mode were retained. These targets did not call the LLM or embedding model. Raw execution files retain Unassessed capture labels; review.json records the subsequent verdict.

Already executed. To reproduce this explicitly scoped harness in new private databases/evidence folders:

~~~powershell
.\.venv\Scripts\python.exe -B audit\scripts\run_ir14.py --route-harness
~~~

The default command without --route-harness requests the full application; its saved attempt is blocked by Windows Application Control. No policy workaround is supplied or applied. A later full-app attempt belongs in a new evidence run when the legitimate environment is ready. record_ir14.py only reviews existing captures and must not be rerun after recording.

**Conclusion:** all 15 original-router HTTP role checks PASS, including 12 denied claim attempts and three allowed controls. IR-14 remains partially assessed because full-app startup/integration is blocked. No new vulnerability is confirmed, IR-13 remains open, and IR-15 is not run.
