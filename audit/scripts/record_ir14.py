"""Review IR-14 saved evidence only; no HTTP, application imports or baseline edits."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import parse_qs,urlparse
import ast,csv,hashlib,io,json,re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'; RUN=AUDIT/'evidence/IR-14/run-20260923T021324976415Z'; FAILED=AUDIT/'evidence/IR-14/run-20260923T020808917231Z'; REL=RUN.relative_to(AUDIT).as_posix()
ROLES=['CUSTOMER','IT_SUPPORT','KNOWLEDGE_ANALYST','ADMIN','AUDIT_VIEWER']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name,folder=RUN): return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def save(name,value): write(RUN/(name+'.json'),json.dumps(value,indent=2,ensure_ascii=False))
def hashes(folder): return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
assert not (RUN/'review.json').exists(), 'Already reviewed; do not rerun writer'
prior={name:hashes(AUDIT/'evidence'/name) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,14)]}; raw_before=hashes(RUN); failed_before=hashes(FAILED)
proc=read('process_result'); planned=read('inputs'); preconditions=read('preconditions'); scope=read('scope_adjustment')
assert proc['completed_worker_count']==5 and proc['total_HTTP_requests']==25 and proc['target_requests']==15
assert all(proc[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged'))
assert all(sha(ROOT/p)==value for p,value in preconditions['prior_evidence_sha256'].items())
assert scope['preserved_failed_attempt_sha256']==failed_before
baseline=read('environment',AUDIT/'evidence/baseline'); assert all(sha(ROOT/name)==digest for name,digest in baseline['source_sha256'].items()) and sha(ROOT/'knowgap.db')==baseline['original_database_sha256']
backup=read('database_backup',AUDIT/'evidence/baseline'); assert sha(Path(backup['path']))==backup['backup_sha256']
failed=read('process_result',FAILED); failed_e=read('execution',FAILED/'CUSTOMER')
assert failed['total_HTTP_requests']==failed['target_requests']==0 and failed['workers'][0]['process_exit_code']==1 and not failed['workers'][0]['timed_out']
assert failed_e['error']['type']=='OSError' and 'WinError 4551' in failed_e['error']['message'] and 'torch_python.dll' in failed_e['error']['message']
assert not failed_e.get('server_started',False) and failed_e['server_stopped']
assert all(failed[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged'))
rows=[]; role_results=[]; snapshots=[]; approved_fields=[]
for role in ROLES:
 folder=RUN/role; e=read('execution',folder); pre=read('database_preflight',folder); post=read('postflight',folder); inputs=read('inputs',folder); login=read('login',folder); profile=read('profile_control',folder); mode=read('runtime_mode',folder); routes=read('route_preflight',folder); worker=read('process_result',folder); snapshot=read('isolated_database_backup',folder)
 assert e['status']=='Executed; awaiting role and mutation review' and e['server_started'] and e['server_stopped'] and not e['full_application_loaded']
 assert (e['login_requests'],e['profile_requests'],e['target_requests'],e['redirect_followups'])==(1,1,3,0)
 assert worker['process_exit_code']==0 and not worker['timed_out'] and worker['server_stopped']
 assert not e['llm']['configured_enabled'] and e['llm']['calls']==0
 assert not mode['full_application_loaded'] and mode['global_dependencies']==mode['user_middleware_count']==mode['dependency_overrides_count']==0
 assert login['status']==303 and login['location']=='/home' and login['cookie_present'] and login['redirect_history_count']==0 and not login['credentials_recorded']
 assert profile['status']==200 and profile['profile_form_present'] and profile['login_proven_by_original_helper'] and profile['database_unchanged'] and profile['redirect_history_count']==0
 assert pre['fixtures']['article']['status']=='draft' and not pre['fixtures']['article']['authoritative'] and pre['fixtures']['categories']==[]
 assert len(pre['tables'])==10 and pre['tables']['knowledgearticle']['row_count']==81 and pre['tables']['ticket']['row_count']==500 and pre['tables']['user']['row_count']==(5 if role=='AUDIT_VIEWER' else 4)
 assert snapshot['integrity_check']=='ok' and snapshot['outside_repository'] and snapshot['all_table_states_match_seeded_source'] and sha(Path(snapshot['path']))==snapshot['sha256']
 assert post['private_snapshot_unchanged'] and post['original_user_rows_unchanged'] and post['ticket_rows_unchanged']
 assert pre['fixtures']['other_articles_sha256']==post['fixtures']['other_articles_sha256']
 snapshots.append({'role':role,'path':snapshot['path'],'sha256':snapshot['sha256'],'verified':True})
 for target in inputs['targets']:
  ident=target['id']; q=read('request',folder/ident); r=read('response',folder/ident); before=read('before',folder/ident); after=read('after',folder/ident); identities=read('resolved_identity',folder/ident)
  allowed=(role=='KNOWLEDGE_ANALYST' and ident=='R01') or (role=='ADMIN' and ident in ('R02','R03'))
  expected_status=200 if role=='ADMIN' and ident=='R02' else 303 if allowed else 403
  assert q['expected_allowed']==allowed and q['expected_status']==expected_status and r['status']==expected_status
  assert q['method']==target['method'] and q['path']==target['path'] and q['query']==target['query'] and q['declared_form']==target['body']
  assert parse_qs(urlparse(q['url']).query)=={k:[v] for k,v in q['query'].items()}
  assert parse_qs(q['serialized_body'])=={k:[v] for k,v in (q['declared_form'] or {}).items()}
  assert q['cookie_present'] and q['cookie_value']=='omitted' and not q['authorization_header_present'] and not q['follow_redirects']
  assert r['redirect_history_count']==0 and not r['set_cookie_present'] and len(r['body_text'].encode('utf-8'))==r['response_bytes'] and hashlib.sha256(r['body_text'].encode('utf-8')).hexdigest()==r['body_sha256']
  assert len(identities)==1 and identities[0]['request_id']==ident and identities[0]['path']==q['path'] and identities[0]['user_found'] and identities[0]['active'] and identities[0]['database_user_id']==e['test_identity']['database_user_id'] and identities[0]['stored_role']==role
  assert after['returned_identity_matches_login'] and after['users_unchanged'] and after['status_matches_expected']
  assert before['fixtures']['other_articles_sha256']==after['fixtures']['other_articles_sha256']
  assert before['tables']['user']==after['tables']['user'] and before['tables']['ticket']==after['tables']['ticket']
  claimed=q['query'] if ident=='R02' else q['declared_form'] or {}
  if not allowed:
   assert claimed['role']==('KNOWLEDGE_ANALYST' if ident=='R01' else 'ADMIN') and claimed['user_id']!=str(e['test_identity']['database_user_id'])
   assert before=={'tables':after['tables'],'fixtures':after['fixtures']} and after['changed_tables']==[] and after['unauthorized_state_unchanged']
   assert r['location'] is None
   if ident=='R01': assert r['body_json']=={'detail':'Knowledge Analyst role required'}
   else: assert r['body_text']=='Admin access required' and r['body_json'] is None
   effect='No table or fixture changes'
  elif ident=='R01':
   assert after['changed_tables']==['knowledgearticle'] and before['tables']['knowledgearticle']['row_count']==after['tables']['knowledgearticle']['row_count']==81
   assert r['location']=='/knowledge' and r['response_bytes']==0
   a=before['fixtures']['article']; b=after['fixtures']['article']; approved_fields=[k for k in a if a[k]!=b[k]]
   assert set(approved_fields)=={'status','authoritative','updated_at'} and a['status']=='draft' and b['status']=='approved' and b['authoritative'] and b['updated_at']>a['updated_at']
   assert before['fixtures']['categories']==after['fixtures']['categories']==[]
   effect='Only fixture approved; authoritative true; updated_at changed'
  elif ident=='R02':
   assert after['changed_tables']==['category'] and before['fixtures']['article']==after['fixtures']['article'] and before['fixtures']['categories']==[]
   cats=after['fixtures']['categories']; assert len(cats)==8 and {x['name'] for x in cats}==set(routes['admin_default_categories']) and all(x['description']=='' and x['is_active'] for x in cats)
   assert 'action="/admin/categories/create"' in r['body_text'] and 'action="/admin/users/create"' in r['body_text'] and r['location'] is None
   effect='Admin HTML returned; eight missing default categories created'
  else:
   assert after['changed_tables']==['category'] and before['fixtures']['article']==after['fixtures']['article'] and r['location']=='/admin?message=Category+created.' and r['response_bytes']==0
   a=before['fixtures']['categories']; b=after['fixtures']['categories']; assert len(a)==8 and len(b)==9 and b[:8]==a and b[-1]['name']==planned['category_fixture']['name'] and b[-1]['description']==planned['category_fixture']['description'] and b[-1]['is_active']
   effect='Exactly one requested active category added; previous eight unchanged'
  for table in before['tables']:
   if table not in after['changed_tables']: assert before['tables'][table]==after['tables'][table]
  rows.append({'role':role,'id':ident,'method':q['method'],'endpoint':q['path'],'expected_allowed':allowed,'http_status':r['status'],'location':r['location'] or '', 'resolved_user_id':identities[0]['database_user_id'],'resolved_role':identities[0]['stored_role'],'claimed_role':claimed.get('role',''),'changed_tables':','.join(after['changed_tables']),'effect':effect,'outcome':'PASS','evidence':f'{role}/{ident}/response.json'})
 role_results.append({'role':role,'login_status':login['status'],'profile_status':profile['status'],'targets':3,'stored_identity_confirmed':True,'changed_tables':post['changed_tables_since_setup'],'final_article_status':post['fixtures']['article']['status'],'final_category_count':len(post['fixtures']['categories']),'other_80_articles_unchanged':True,'all_accounts_and_500_tickets_unchanged':True,'server_stopped':True})
assert len(rows)==15 and sum(x['expected_allowed'] for x in rows)==3
assert all(p.name=='.gitkeep' for p in (AUDIT/'evidence/IR-15').rglob('*') if p.is_file())
# No artifact writes occur above: all actual response/state evidence is checked before review generation.
save('role_matrix',rows)
stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows); (RUN/'role_matrix.csv').write_text(stream.getvalue(),encoding='utf-8',newline='\n')
save('authorization_review',{'scope':'Original-router HTTP integration; not full app.main runtime','target_checks':15,'passed':15,'denied_checks':12,'allowed_controls':3,'role_results':role_results,'article_changed_fields_for_analyst_only':approved_fields,'ordinary_field_claims_ignored':True,'unsupported_fixture':'Active AUDIT_VIEWER account directly provisioned only in its own private DB, normally logged in, profile 200, all three privileged requests 403. No admin role-assignment API bypass inferred.','GET_admin_observation':'ADMIN page created eight expected categories after guard; no other role did. Captured expected behavior, not independently a vulnerability finding or CSRF test.','new_vulnerability_identified':False,'existing_VULN_IR13_01':'Open; unchanged; not remediated or retested by this case'})
save('full_application_attempt_review',{'evidence_directory':FAILED.relative_to(ROOT).as_posix(),'outcome':'Blocked / Inconclusive; no authorization verdict','failure':failed_e['error'],'HTTP_requests':0,'server_started':False,'source_database_and_prior_evidence_unchanged':True,'preserved_raw_sha256':failed_before,'followup':'Separately predeclared original-router HTTP harness; no OS/DLL/package/app changes'})
save('review',{'test_id':'IR-14','test_name':'Unauthorized Role Access','status':'Partially assessed','route_HTTP_outcome':'PASS (15/15 checks across five roles)','full_application_outcome':'Blocked / Inconclusive (WinError 4551 during import, zero HTTP)','vulnerability_identified':'No new vulnerability demonstrated in the tested guards','severity':'Not applicable for passing route checks; environment blocker is not an authorization vulnerability','existing_VULN_IR13_01':'Confirmed Medium; open; unchanged','total_actual_HTTP_requests':25,'redirect_followups':0,'LLM_calls':0,'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'limits':['Original-router HTTP harness only; full app startup/integration not verified','Synthetic data and active accounts; three privileged routes only','No crafted tokens, expired/inactive credentials, CSRF, ownership or other privileged endpoint coverage','Unsupported role is a direct private fixture, not account-creation API evidence'],'next_case':'IR-15 not run'})
record=[
 '## IR-14 - Unauthorized Role Access','',
 '- Test ID: IR-14',
 '- Test Name: Unauthorized Role Access',
 '- Test Objective: Verify that successful login grants only the stored role permissions and that submitted role/user_id fields cannot confer privileges.',
 '- Component Being Tested: Original auth.login(), auth.profile_page(), auth.current_user_from_request(), knowledge.approve_article(), admin._admin_user(), admin.admin_page(), admin._ensure_categories() and admin.create_category(); SQLModel persistence and original templates.',
 '- Input / Attack Scenario: CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, ADMIN and active unsupported AUDIT_VIEWER each send one POST /knowledge/81/approve, GET /admin and POST /admin/categories/create. Twelve denied-role attempts include claimed privileged role and another user_id in form/query fields; positive controls use normal fields. Draft AUDIT-IR14-DRAFT-001 and category IR14 Audit Category are synthetic fixtures.',
 '- Preconditions: Original source/main database and private Phase 1 backup verified. Fresh seeded private database and pre-request snapshot per role; 80 original articles plus one draft, 500 tickets, four seed accounts (five only in unsupported-role worker). Normal login 303 /home, issued cookie present and authenticated profile 200 confirmed before every role sequence.',
 '- Steps: Preserve failed full-app attempt; predeclare reduced scope; mount unchanged auth/knowledge/admin routers in isolated FastAPI HTTP harness; snapshot private database; login/profile control; submit three declared requests with redirects disabled; compare resolved identity and all table states after each; verify nonfixture articles and snapshots; stop owned servers; review saved evidence.',
 '- Expected Behaviour: Only KNOWLEDGE_ANALYST approves the draft; only ADMIN views administration and creates the category. Other roles receive 403 without data or database changes. Permitted actions have only their declared effects, including original category initialization on ADMIN GET.',
 '- Actual Behaviour: Full app import stopped with WinError 4551 on torch_python.dll before any HTTP. Separate original-router harness executed 25 HTTP requests, including all 15 role checks. Twelve denied cases returned 403, retained the logged-in identity and made no table changes. Analyst approval returned 303 /knowledge, changed only draft status/authoritative/updated_at. ADMIN GET returned 200 and created eight defaults; ADMIN category POST returned 303 and added exactly one category. All servers stopped.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), role_matrix.json/CSV, authorization_review.json, full_application_attempt_review.json, review.json, per-role login/profile/preflight/snapshot/postflight files and R01-R03 request/response/identity/before/after captures.',
 '- Observation: The handlers use the stored database role resolved from authenticated token subject; ordinary request claims did not replace identity. ADMIN has no knowledge-approval override. AUDIT_VIEWER login succeeded but all three privileged operations were denied. GET /admin has a recorded category-initialization side effect.',
 '- Outcome: Partially assessed overall: PASS for all 15 original-router HTTP checks; full-application verification Blocked / Inconclusive. Startup failure is not an authorization FAIL.',
 '- Vulnerability Identified: No new vulnerability demonstrated in the tested role guards. VULN-IR13-01 remains confirmed Medium and open; this case neither fixes nor retests its agent endpoints.',
 '- Impact: No unauthorized privileged data or persistent mutation observed in these checks. Authorized changes were confined to temporary fixture/article and category tables.',
 '- Likelihood: No bypass demonstrated; prevalence or exploit likelihood cannot be inferred from this bounded passing sample.',
 '- Severity: Not applicable for passing role checks. The environment blocker is not classified as an authorization vulnerability.',
 '- Technical Explanation: current_user_from_request() verifies the issued token and loads User by sub. approve_article() requires KNOWLEDGE_ANALYST; _admin_user() requires ADMIN before admin data/mutation. Extra form/query role/user_id values do not participate in these checks. The harness retains original APIRoutes and dependencies with no overrides; identity observation calls the original helper and returns its result unchanged.',
 '- Recommended Mitigation: No role-guard repair supported by this case. Retain explicit per-operation checks and these positive/negative controls. Complete a full-app rerun when the legitimate environment can load its dependencies; no Windows policy, DLL, dependency or application changes were made. The separate IR-13 remediation remains pending.',
 '- Conclusion: Correct role enforcement observed across five active roles and three original routers, including field-claim attempts. Full-app startup/integration remains unverified. Stop before IR-15.',
 '- Testing Limitations: Local synthetic dataset, original-router HTTP harness only, five active roles and three privileged endpoints. No JWT forgery, expiry/revocation, inactive-account, role-assignment API, object ownership, CSRF, alternative route, production, external or load tests. Redirects were not followed; no browser asset requests. Groq disabled and zero calls. Private main-file integrity checks do not cover unrelated concurrent WAL writes.',
]
notes=[
 '# IR-14 - Unauthorized Role Access','',
 '**Status: Partially assessed. All 15 original-router HTTP role checks PASS. Full-application verification is Blocked / Inconclusive. No new authorization vulnerability was demonstrated; VULN-IR13-01 remains open.**','',
 '## Runtime scope and preserved startup failure','',
 'The first attempt, [run-20260923T020808917231Z](../run-20260923T020808917231Z/process_result.json), failed while importing app.main. Windows Application Control returned WinError 4551 for torch_python.dll or a dependency. The stack passed through tickets/coordinator/retrieval/embeddings into PyTorch. No server started and zero login, profile or target requests were sent. This is an environment limitation, not an authorization FAIL. The original logs, inputs and integrity checks remain preserved.','',
 'The successful run was separately predeclared as a smaller HTTP integration test. An audit FastAPI app mounted the original auth, knowledge and admin routers, original static directory and original create_db_and_tables startup. Their handlers, SQLModel dependencies, templates, password verification, cookie issuance and role checks remained original. No dependency overrides, custom middleware or app-wide dependencies were installed. Source inspection of app/main.py confirms these routers have no additional registration-time guards. Identity observers called the original helper once per invocation and returned its unchanged user.','',
 'The harness does not load app.main or the retrieval stack and does not establish that the complete application currently starts. It does not load a substitute PyTorch module or change Windows policy, DLLs, installed packages or app source. Only the three declared privileged routes and login/profile controls were requested; redirect destinations were captured and not followed. Read [scope_adjustment.json](scope_adjustment.json), per-role runtime_mode.json and [full_application_attempt_review.json](full_application_attempt_review.json).','',
 '## Case record','',
 *record[2:],'',
 '## Actual role matrix','',
 '| Authenticated stored role | POST /knowledge/81/approve | GET /admin | POST /admin/categories/create | Result |',
 '|---|---|---|---|---|',
 '| CUSTOMER | 403; no change | 403; no change | 403; no change | PASS |',
 '| IT_SUPPORT | 403; no change | 403; no change | 403; no change | PASS |',
 '| KNOWLEDGE_ANALYST | 303 /knowledge; fixture approved | 403; no change | 403; no change | PASS |',
 '| ADMIN | 403; no change | 200; eight defaults added | 303 /admin success; one category added | PASS |',
 '| AUDIT_VIEWER (unsupported fixture) | 403; no change | 403; no change | 403; no change | PASS |','',
 'All five normal login attempts returned 303 /home with an issued cookie; all five profile controls returned 200 and resolved the expected active user ID and stored role. Each target also resolved that same identity exactly once. These controls distinguish authenticated role denial from accidental unauthenticated rejection. Total traffic was 25 requests: five logins, five profiles and fifteen targets. The failed full-app attempt contributed zero requests. No automatic redirects, provider calls or browser asset requests occurred.','',
 '## Exact fixtures and request fields','',
 'Every role started in a new process/database with the original 80 synthetic articles, 500 tickets and four seed users. One draft fixture became article ID 81: doc_id AUDIT-IR14-DRAFT-001, title IR14 role approval fixture, category Printers, source_type internal_kb, status draft, authoritative false, supported_os Any, security_class internal, created_at/updated_at 2026-09-22T00:00:00. Its harmless content is: Synthetic audit note for testing knowledge approval. No troubleshooting action is requested. All complete fixture values are in [inputs.json](inputs.json).','',
 'Only the AUDIT_VIEWER database had a fifth active account provisioned directly as an isolated fixture. It used an existing synthetic credential privately; no credential or hash is included in the report. This demonstrates rejection of an authenticated unsupported role by the three guards; it does not show that a role-assignment API permits that role.','',
 '| Request | Allowed positive input | Denied-role claim added |',
 '|---|---|---|',
 '| R01 POST /knowledge/81/approve | No form body | Form role=KNOWLEDGE_ANALYST, user_id=3, status=approved, authoritative=true |',
 '| R02 GET /admin | No query | Query role=ADMIN and user_id=4 |',
 '| R03 POST /admin/categories/create | Form name=IR14 Audit Category, description=Synthetic category for role authorization check. | Same valid form plus role=ADMIN, user_id=4 |','',
 'Every request carried the normal cookie for its own logged-in account. Cookie presence is recorded, but values are omitted. No Authorization header, forged token, cookie substitution or stored-role change was used. Exact URL, encoded body and expected outcome are saved in each role/R01-R03/request.json. Across all 12 denied attempts, submitted role/user_id claims did not replace the observed identity.','',
 '## Responses and persistent effects','',
 'Every denied approval returned the 44-byte JSON body {"detail":"Knowledge Analyst role required"}; denied admin requests returned the 21-byte text Admin access required. All denied requests left all ten table counts and row hashes unchanged. There were no protected page bodies on denied admin requests.','',
 'KNOWLEDGE_ANALYST approval returned an empty 303 body with Location /knowledge. The only changed fixture fields were status (draft to approved), authoritative (false to true), and updated_at. Row count stayed 81. A separate digest, plus independent read-only comparison with the private snapshot, confirmed all other 80 articles were identical. Users, tickets, categories and all other tables were unchanged.','',
 'ADMIN GET /admin returned 200 with 21,584 bytes of actual admin HTML. The original _ensure_categories() added exactly eight active categories with empty descriptions: Accounts / Passwords, Outlook / MFA, Printers, Remote Desktop, Software Installation, VPN, Wi-Fi / DNS, Windows / Updates. This happened after the ADMIN guard; no denied caller triggered category initialization. The later create request returned empty 303 with Location /admin?message=Category+created. and added exactly the ninth category, matching the submitted name/description and active=true; the previous eight rows stayed identical. This observed GET side effect alone is not classified as a separate vulnerability, and no CSRF test was performed.','',
 'ADMIN could not approve the draft. CUSTOMER, IT_SUPPORT and AUDIT_VIEWER ended with every table unchanged, draft unapproved and zero categories. KNOWLEDGE_ANALYST ended with the one approved fixture and zero categories. ADMIN ended with an unapproved draft and nine categories. All original account rows and 500 ticket rows remained identical in every worker. The original working database was never a test target.','',
 '## Technical explanation','',
 'In [auth.py](../../../../app/routes/auth.py), current_user_from_request() decodes access_token, reads its sub and loads the database User. Normal login checks active state and password, then issues the cookie; profile_page() provides the authenticated control. The role here came from the loaded database record. In [knowledge.py](../../../../app/routes/knowledge.py), approve_article() checks user.role == KNOWLEDGE_ANALYST before loading and modifying the article. In [admin.py](../../../../app/routes/admin.py), _admin_user() requires ADMIN, and both admin_page() and create_category() reject other users before returning admin data or committing their changes. None of these guards reads the submitted role/user_id claim.','',
 'These exact checks explain the observed status and state matrix. They do not prove every route is protected: the separate VULN-IR13-01 missing-authentication finding remains confirmed Medium and open. The startup blocker is also distinct from access-control behavior.','',
 '## Evidence, integrity and reproduction','',
 '| Files | Purpose |','|---|---|',
 '| inputs.json, expected_result.md, scope_adjustment.json | Criteria and explicit reduced runtime scope fixed before the harness requests |',
 '| preconditions.json, process_result.json | Baseline source/database/backup, prior evidence and aggregate request/runtime checks |',
 '| ROLE/inputs.json, route_preflight.json, runtime_mode.json | Exact fields, original handler source and harness construction |',
 '| ROLE/login.json, profile_control.json/HTML | Actual login and authenticated profile control without credentials |',
 '| ROLE/isolated_database_backup.json, database_preflight.json | Consistent private snapshot before login/targets and initial table/fixture states |',
 '| ROLE/R01-R03/request.json, response.json, response_body.txt/HTML | Built nonsecret request, original status/Location/full response, byte length and hash |',
 '| ROLE/R01-R03/resolved_identity.json, before.json, after.json | Stored identity and per-request all-table/fixture comparison |',
 '| ROLE/postflight.json, execution.json, process_result.json, terminal_log.txt | Final state, zero LLM calls, shutdown and timings |',
 '| role_matrix.json/CSV, authorization_review.json, review.json | Later reviewed per-request outcomes and explicit overall limits |',
 '| full_application_attempt_review.json, evidence_integrity.json | Earlier startup failure classification and raw-evidence preservation |','',
 'Five private SQLite snapshots were made after fixture/setup and before login or test requests. Each passed integrity_check and matched all seeded table fingerprints; each snapshot hash still matches after testing. Raw databases remain outside the repository because they contain account credential hashes. Only nonsecret role metadata, fixture/category rows and table hashes are exported. The original Phase 1 private backup is also verified. Source hashes, original working-DB main-file hash, baseline and IR-01 through IR-13 evidence, and the failed full-app captures remain unchanged.','',
 f"The harness run finished at {proc['finished_at_utc']} and took {proc['elapsed_seconds']} seconds across five sequential workers. All worker exits were 0, without timeouts; all owned servers stopped. The same numerical-library thread settings, scoring configuration and disabled Groq mode were retained. These targets did not call the LLM or embedding model. Raw execution files retain Unassessed capture labels; review.json records the subsequent verdict.",'',
 'Already executed. To reproduce this explicitly scoped harness in new private databases/evidence folders:','',
 '~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir14.py --route-harness','~~~','',
 'The default command without --route-harness requests the full application; its saved attempt is blocked by Windows Application Control. No policy workaround is supplied or applied. A later full-app attempt belongs in a new evidence run when the legitimate environment is ready. record_ir14.py only reviews existing captures and must not be rerun after recording.','',
 '**Conclusion:** all 15 original-router HTTP role checks PASS, including 12 denied claim attempts and three allowed controls. IR-14 remains partially assessed because full-app startup/integration is blocked. No new vulnerability is confirmed, IR-13 remains open, and IR-15 is not run.','']
notes=[line.replace(f'[{REL}/notes.md]({REL}/notes.md)','[notes.md](notes.md)') for line in notes]
write(RUN/'notes.md','\n'.join(notes))
progress='IR-14 is partially assessed: all 15 original-router HTTP role checks PASS, while full-app startup is blocked by Windows Application Control (WinError 4551). No new vulnerability identified; VULN-IR13-01 remains open. IR-15 remains Not run.'
for name,area in [('test_results.md','Authorization'),('test_plan.md','Authorization / RBAC')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert 'IR-14 and IR-15 remain Not run.' in text
 text=text.replace('IR-14 and IR-15 remain Not run.',progress,1)
 text,count=re.subn(r'^\| IR-14 \|.*$',f'| IR-14 | {area} | Partially assessed (original-router HTTP) | [{REL}/notes.md]({REL}/notes.md) | PASS (15 route checks); full app Blocked / Inconclusive | NO new vulnerability demonstrated |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-14[^\n]*\n.*?(?=^## IR-15)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('and the partially assessed IR-03 case.','and the partially assessed IR-03 and IR-14 cases (IR-14 route checks pass; full-app startup blocked).',1)
text=text.replace('- evidence/IR-01/ through evidence/IR-13/: actual case evidence, including retrieval checks and the confirmed unauthenticated agent-access finding; IR-14 and IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-14/: actual case evidence, including retrieval checks, the confirmed unauthenticated agent-access finding, and scoped IR-14 role checks with a preserved full-app startup blocker; IR-15 remains reserved.',1)
text=text.replace('IR-14 and IR-15 remain Not run.',progress+f' See [{REL}/notes.md]({REL}/notes.md).',1)
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8'); assert 'IR-14/ and IR-15/ contain placeholders only.' in text
text=text.replace('IR-14/ and IR-15/ contain placeholders only.',f'IR-14/run-20260923T020808917231Z/ preserves a full-app import failure (WinError 4551; zero HTTP). IR-14/{RUN.name}/ records the separate original-router HTTP harness: 25 requests, all 15 role checks PASS and only expected authorized database changes. IR-14 is partially assessed because full-app integration remains blocked; no new vulnerability. IR-15/ contains a placeholder only.',1)
write(path,text)
additions={
 'vulnerability_register.md':f'''## IR-14 role-guard review - no new vulnerability

All 15 checks across five normally logged-in active roles and three privileged endpoints passed in the original-router HTTP harness. Twelve attempts carrying claimed privileged role/user_id fields returned 403 without persistent changes; authorized analyst approval and ADMIN operations made only expected changes in private synthetic databases. The unsupported active AUDIT_VIEWER fixture was denied all three operations; its direct provisioning/login is not proof of a role-assignment API bypass. ADMIN correctly could not approve the article.

The full app import failed with Windows Application Control WinError 4551 at torch_python.dll before any HTTP; IR-14 is therefore partially assessed. This environment failure is not classified as an authorization vulnerability. ADMIN GET initialization of eight missing categories is documented as existing behavior; this case does not establish a CSRF weakness. No new finding/severity is assigned. VULN-IR13-01 remains confirmed Medium, open and unchanged, and no fix was applied. See [{REL}/notes.md]({REL}/notes.md). IR-15 is not run.
''',
 'risk_matrix.md':f'''## IR-14 assessment

No additional vulnerability rating is introduced. All 15 original-router HTTP checks pass: 12 denied role-claim attempts have no changes, and three allowed controls produce only expected fixture/category changes. Full-application verification remains blocked by the observed Windows Application Control dependency error. Passing these three route guards does not close VULN-IR13-01 or establish application-wide authorization. See [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':f'''## IR-14 observed result

I tested three privileged routes under CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, ADMIN and a directly provisioned active unsupported AUDIT_VIEWER fixture. Each role used a separate private seeded database, a normal login and a profile 200 control. I observed the database identity resolved by the original helper so a 403 could not be misreported as a role denial after failed login. Twelve denied attempts carried privileged role/user_id claims in ordinary fields; none changed identity or any database row.

Only the analyst approved the fixture. Only ADMIN viewed the admin page and created the category; ADMIN could not approve knowledge. The admin GET intentionally initialized eight missing categories, then the create POST added one. I verified exact mutations and unchanged nonfixture articles/accounts/tickets, rather than judging access solely from status codes.

The full app could not import because Windows Application Control blocked torch_python.dll. I preserved that zero-request failure and separately tested the unchanged original routers through HTTP in a smaller audit FastAPI app. Thus 15/15 router checks PASS, but IR-14 is partially assessed and full-app integration remains blocked. I did not alter Windows policy or substitute security guards. No new vulnerability was found; the earlier Medium missing-authentication agent finding remains open. See [{REL}/notes.md]({REL}/notes.md). IR-15 is not run.
''',
 'commands.md':f'''## IR-14 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir14.py --route-harness
~~~

Already executed once in this explicit scope. The harness mounts the unchanged original auth, knowledge and admin routers, snapshots five private synthetic databases and sends five normal logins, five profile controls and 15 declared role checks. It saves nonsecret requests/responses and per-request state/identity checks, then stops its servers. All 15 route checks passed. No test credentials are printed.

The default command without --route-harness imports the full application; the preserved attempt was blocked with WinError 4551 on torch_python.dll before any HTTP. The flag selects a documented router-level test and does not fix or certify full-app startup. No Windows control change or blocked-DLL execution is performed. See [{REL}/notes.md]({REL}/notes.md). record_ir14.py derives the report from saved captures without HTTP and must not be rerun after recording. IR-15 remains unexecuted.
''',
 'endpoint_inventory.md':f'''## IR-14 runtime addendum

Original-router HTTP integration confirmed the following intended roles with normal login/profile controls and five separate synthetic databases:

| Endpoint | Method | Allowed role observed | Other tested roles | Persistent effects of allowed request |
|---|---|---|---|---|
| /knowledge/81/approve | POST | KNOWLEDGE_ANALYST (303) | CUSTOMER, IT_SUPPORT, ADMIN, AUDIT_VIEWER: 403 | Only fixture status, authoritative and updated_at changed |
| /admin | GET | ADMIN (200) | CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, AUDIT_VIEWER: 403 | Eight missing default categories initialized |
| /admin/categories/create | POST | ADMIN (303) | CUSTOMER, IT_SUPPORT, KNOWLEDGE_ANALYST, AUDIT_VIEWER: 403 | One submitted active category created |

Denied callers submitted privileged role/user_id claims in ordinary fields, but the resolved identity remained their authenticated database user and all tables stayed unchanged. This is evidence for these original routers only. Full-app startup was blocked by Windows Application Control before any HTTP in a separate attempt, so IR-14 remains partially assessed. No finding from IR-13 is closed and no additional routes were tested. See [{REL}/notes.md]({REL}/notes.md).
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert addition.splitlines()[0] not in text; write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before_hashes for name,before_hashes in prior.items())
assert all(sha(ROOT/name)==digest for name,digest in raw_before.items()) and hashes(FAILED)==failed_before
assert all(p.name=='.gitkeep' for p in (AUDIT/'evidence/IR-15').rglob('*') if p.is_file())
save('evidence_integrity',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'prior_evidence_directories_unchanged':list(prior),'prior_file_counts':{name:len(value) for name,value in prior.items()},'original_IR14_captures_unchanged':True,'raw_capture_sha256':raw_before,'failed_full_application_attempt_unchanged':True,'failed_attempt_sha256':failed_before,'source_files_match_baseline':True,'working_database_main_file_matches_baseline':True,'verified_private_snapshots':snapshots,'IR15_unexecuted':True})
print('IR-14 recorded: 15/15 original-router HTTP role checks PASS; full-app import blocked (zero requests), overall partially assessed. No new vulnerability. IR-13 unchanged/open; IR-15 not run.')
