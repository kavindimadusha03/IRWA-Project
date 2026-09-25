"""Record the completed IR-13 authentication audit from saved evidence only."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import parse_qs
import csv,hashlib,io,json,re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'; RUN=AUDIT/'evidence/IR-13/run-20260922T193751545217Z'; REL=RUN.relative_to(AUDIT).as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name,folder=RUN): return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def save(name,value): write(RUN/(name+'.json'),json.dumps(value,indent=2,ensure_ascii=False))
def hashes(folder): return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
assert not (RUN/'review.json').exists(), 'Already reviewed; do not rerun writer'
prior={name:hashes(AUDIT/'evidence'/name) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,13)]}; raw_before=hashes(RUN)
e=read('execution'); proc=read('process_result'); inputs=read('inputs'); before=read('database_preflight'); post=read('database_postflight'); routes=read('route_preflight'); records=read('eligible_records'); corpus=read('corpus_preflight')
assert e['target_requests']==4 and e['login_requests']==e['redirect_followups']==0 and e['endpoint_calls']=={'retrieval':1,'knowledge':1}
assert e['server_started'] and e['server_stopped'] and proc['process_exit_code']==0 and not proc['timed_out']
assert all(proc[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged'))
assert not e['llm']['configured_enabled'] and e['llm']['chat_attempts']==e['llm']['successful_returns']==0
assert all(post[k] for k in ('all_tables_unchanged','seeded_database_main_file_unchanged','private_snapshot_unchanged','ticket_count_unchanged')) and post['tables']==before['tables']
assert len(before['tables'])==10 and before['tables']['ticket']['row_count']==500 and before['tables']['knowledgearticle']['row_count']==80 and before['tables']['user']['row_count']==4
assert corpus['schema_valid'] and corpus['ticket_form_meets_length_rules'] and corpus['matches_original_CSV_in_all_retrieval_fields'] and len(records)==427
backup=read('isolated_database_backup'); assert backup['integrity_check']=='ok' and backup['outside_repository'] and backup['all_table_states_match_seeded_source'] and sha(Path(backup['path']))==backup['sha256']
baseline=read('environment',AUDIT/'evidence/baseline'); assert all(sha(ROOT/name)==digest for name,digest in baseline['source_sha256'].items()) and sha(ROOT/'knowgap.db')==baseline['original_database_sha256']
request_rows=[]; responses={}
for target in inputs['targets']:
 ident=target['id']; q=read('request',RUN/ident); r=read('response',RUN/ident); db=read('database_after',RUN/ident)
 assert q['method']==target['method'] and q['path']==target['path'] and q['declared_body']==target['body'] and q['fresh_client'] and not q['follow_redirects'] and not q['trust_env']
 assert not q['cookie_header_present'] and not q['authorization_header_present'] and not q['proxy_authorization_header_present'] and q['client_cookie_count_before']==0
 assert r['redirect_history_count']==0 and r['client_cookie_count_after']==0 and not r['set_cookie_header_present'] and r['no_authentication_sent']
 assert len(r['body_text'].encode('utf-8'))==r['response_bytes'] and hashlib.sha256(r['body_text'].encode('utf-8')).hexdigest()==r['response_text_sha256']
 assert db['all_tables_equal_pre_request_snapshot'] and db['tables']==before['tables'] and db['ticket_rows_hash_unchanged'] and db['ticket_count_before']==db['ticket_count_after']==500
 if target['encoding']=='form': assert parse_qs(q['serialized_body'])=={k:[v] for k,v in target['body'].items()}
 if target['encoding']=='json': assert json.loads(q['serialized_body'])==target['body']
 if ident in ('A01','A02'): assert r['status_code']==303 and r['location']=='/' and r['response_bytes']==0
 else: assert r['status_code']==200 and r['location'] is None and r['body_json'] and r['content_type']=='application/json'
 responses[ident]=r
 request_rows.append({'id':ident,'method':q['method'],'endpoint':q['path'],'credentials_sent':False,'status':r['status_code'],'location':r['location'] or '', 'body_bytes':r['response_bytes'],'database_unchanged':True,'outcome':'PASS' if ident in ('A01','A02') else 'FAIL','reason':'Login redirect with empty body and no mutation' if ident in ('A01','A02') else 'Internal retrieval source text returned' if ident=='A03' else 'Knowledge-health aggregate data returned'})
r=responses['A03']['body_json']; health=responses['A04']['body_json']; source_map={x['source_id']:x for x in records}
assert r==read('retrieval_function_result')['result'] and health==read('knowledge_function_result')['result']
assert [x['source_id'] for x in r['items']]==['SYN-0138','SYN-0033','KB-001','SYN-0037','SYN-0027'] and len(r['items'])==5
returned=[]
for item in r['items']:
 expected=source_map[item['source_id']]; assert all(item[k]==v for k,v in expected.items())
 returned.append({'source_id':item['source_id'],'title':item['title'],'source_type':item['source_type'],'status':item['status'],'content':item['content'],'category':item['category'],'score':item['hybrid_score'],'all_original_retrieval_fields_match_seeded_record':True})
assert len(health['health'])==5 and health['clusters']==[]
h=read('knowledge_function_result'); assert not h['cache_before']['cache_present'] and h['cache_before']['cache_time']==0 and h['cache_present_after']
assert routes['global_dependencies']==0 and routes['user_middleware_count']==0
for target in routes['targets']:
 assert target['direct_dependencies']==[{'name':'session','call':'get_session','nested_dependency_count':0}]
 if target['id'] in ('A03','A04'): assert 'current_user_from_request' not in target['handler_source']
save('endpoint_results',{'case':'IR-13','overall_outcome':'FAIL','targets':request_rows,'request_scope':'One actual HTTP request per target; fresh no-cookie/no-Authorization clients; no redirects followed','intended_policy':'Sensitive internal agent operations require authentication even though baseline source inventory accurately describes them as currently Public'})
buf=io.StringIO(newline=''); writer=csv.DictWriter(buf,fieldnames=list(request_rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(request_rows); write(RUN/'endpoint_results.csv',buf.getvalue())
save('disclosure_review',{'retrieval':{'anonymous_response_bytes':responses['A03']['response_bytes'],'query':r['query'],'decision':r['decision'],'best_score':r['best_score'],'returned_sources':returned,'observed_data':'Four synthetic historical problem descriptions and resolution notes, one approved internal KB body, source metadata and scores','root_cause_note':'Root cause labels occur in historical content, but all four values are empty; no nonempty root-cause data demonstrated','identity_note':'No credential, account profile, ticket-owner identity or real-user record exposed in this response'},'knowledge_analysis':{'anonymous_response_bytes':responses['A04']['response_bytes'],'result':health,'observed_data':'Five category/count/coverage/gap rows; no clusters or individual examples','source_explanation':'500 seeded tickets: original >60 count-based coverage path and >=120 cluster-skip path. Only process-local cache was populated.'},'policy_context':'Internal intended audit policy and UI guard separation; no external gateway/proxy protection tested','no_persistent_mutation':True,'synthetic_data_only':True})
finding={'vulnerability_id':'VULN-IR13-01','title':'Missing authentication exposes internal agent retrieval and knowledge analytics','related_test':'IR-13','affected_endpoints':['POST /agents/retrieval/search','POST /agents/knowledge/analyze'],'affected_components':['app/routes/agents.py:24-26','app/routes/agents.py:38-40','app/main.py:20,28'],'description':'Clean unauthenticated clients invoke both sensitive agent functions and receive seeded internal source text/analytics. A database dependency opens a session but does not verify identity. Protected UI redirects do not cover direct API routes.','evidence':'A03/request.json and response.json; A04/request.json and response.json; original function results; route_preflight.json; per-request DB hashes','impact':'Unauthorized read access to the demonstrated synthetic source content and internal aggregate analytics. If similarly deployed with sensitive data and reachable by untrusted callers, that data could be exposed. No real-data disclosure, persistence change or account takeover observed.','likelihood':'Straightforward for a caller with network access to this application: valid normal request, no login or user interaction needed. Each target tested once; no prevalence estimate or public network reachability established.','severity':'Medium','risk_level':'Medium (qualitative, tested application scope)','severity_justification':'A demonstrated authentication boundary failure with limited confidentiality impact and easy invocation for a reachable caller. Loopback-only synthetic setting and absence of writes/real-data harm limit claims; High/Critical or an invented CVSS score is not justified.','technical_explanation':'Agent router/handlers omit identity checks and app inclusion adds none. AgentMessage structural fields are not credentials; normal audit_client sender was accepted. Both original functions executed once and their exact results were serialized to anonymous HTTP responses.','recommended_mitigation':'Require a shared verified-current-user or authenticated service-identity dependency on sensitive agent routes; define route/role permissions, with knowledge analysis limited to intended analysts/services. Reject missing/invalid credentials before invoking agents. Add authentication regression tests; do not rely on payload sender strings, obscurity, CORS or an assumed gateway. Scope returned fields to authorized needs.','status':'Confirmed in local synthetic test; open; remediation not applied','limitations':['Only two agent APIs and two UI controls tested once each','No authenticated role matrix, malformed credential or schema-abuse probe','No public/production deployment or real user data','No denial-of-service, broad enumeration, write exploit or privilege escalation demonstrated','Knowledge endpoint returned aggregates only, no cluster examples','Groq disabled and not called; finding independent of generated answers']}
save('finding',finding)
save('review',{'case':'IR-13','reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'Completed (local HTTP; synthetic data)','outcome':'FAIL','target_results':request_rows,'vulnerability_identified':'YES - missing authentication under intended policy','vulnerability_id':finding['vulnerability_id'],'severity':'Medium','formal_vulnerability_added':True,'total_target_requests':4,'login_requests':0,'redirect_followups':0,'provider_calls':0,'all_table_states_unchanged':True,'server_stopped':True,'scope_limits':finding['limitations'],'next_case_not_executed':'IR-14','evidence':'notes.md'})
record=[
 '## IR-13 - Unauthenticated Access','',
 '- Test ID: IR-13',
 '- Test Name: Unauthenticated Access',
 '- Test Objective: Verify whether intended protected UI and sensitive agent operations reject requests without login.',
 '- Component Being Tested: home(), create_ticket(), current_user_from_request(), retrieval_search(), knowledge_analyze(), search_knowledge(), analyze_knowledge_health(), app/router dependency wiring.',
 '- Input / Attack Scenario: One GET /home; one valid POST /tickets/create form; one valid AgentMessage POST /agents/retrieval/search for '+r['query']+'; one bodyless POST /agents/knowledge/analyze. Fresh unauthenticated client per target; exact inputs saved.',
 '- Preconditions: Owned loopback server, original synthetic corpus/users in isolated DB, actual source and working-DB hashes match baseline, original private backup and seeded snapshot verified. No cookies/authorization headers or prior login; no automatic redirect following.',
 '- Steps: Predeclare four requests and policy; validate benign schemas; verify backup/isolation; start owned server and snapshot all tables; send one fresh-client request per target; capture initial status/Location/full body; verify table hashes after each; match exposed data to source and function returns; stop server and review.',
 '- Expected Behaviour: Protected operations redirect to login or return 401/403 without protected data/mutation. Valid 200 internal agent results violate intended policy; source-level Public classification is not a secure-behavior exception.',
 '- Actual Behaviour: /home and /tickets/create returned 303 to / with zero-byte bodies, no ticket created. Both agent APIs returned anonymous 200: retrieval 3284 bytes with four resolved histories plus one KB body; health 384 bytes with five category aggregate rows, clusters empty. No login/provider call, no persistent table changes; server stopped.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), A01-A04 request/response/database_after files, endpoint_results.json/CSV, disclosure_review.json, finding.json, original function results and review.json.',
 '- Observation: Direct agent APIs omit authentication despite guarded UI routes. Request metadata is schema input, not identity. All returned source fields match seeded eligible records; knowledge cache is the only observed nonpersistent side effect.',
 '- Outcome: FAIL overall; A01/A02 PASS and A03/A04 FAIL.',
 '- Vulnerability Identified: YES - VULN-IR13-01, missing authentication on sensitive agent endpoints; one shared root cause covers both failures.',
 '- Impact: Anonymous read access to synthetic internal source text and aggregate analytics demonstrated. Similar reachable deployment with sensitive data could expose it; no real-data breach, ticket mutation, credential disclosure or takeover observed.',
 '- Likelihood: Easy for callers who can reach the service: one valid request, no identity or interaction. Tested once per route on localhost; internet reachability and population prevalence unmeasured.',
 '- Severity: Medium, qualitative under the audit rubric; meaningful but limited demonstrated confidentiality/control weakness. No High/Critical or numeric CVSS claim.',
 '- Technical Explanation: get_session() supplies DB access only. Agent handlers/router and FastAPI inclusion add no verified-user guard; UI handlers explicitly use current_user_from_request(). Anonymous HTTP results exactly match original agent function outputs.',
 '- Recommended Mitigation: After approval, apply shared verified identity and explicit route/role/service permissions before sensitive agent invocation; add absent/invalid credential regression tests and restrict returned data to authorized needs. No fix applied.',
 '- Conclusion: Local runtime confirms missing authentication and data return from two agent APIs while UI denial holds. Register one Medium finding. IR-14 and IR-15 remain unexecuted.',
 '- Testing Limitations: Four requests on an owned localhost server; original synthetic corpus; no real users/public systems, authenticated role testing, token attacks, write exploitation, DoS or deployment/proxy assurance. Groq disabled and unused.',
]
notes=['# IR-13 - Unauthenticated Access','',
 '**Reviewed result: FAIL.** A01/A02 correctly redirect anonymous UI/ticket requests. A03/A04 return internal retrieval and knowledge-health data without authentication. **VULN-IR13-01, Medium:** missing authentication on two sensitive agent APIs, confirmed on an isolated loopback instance with synthetic data. No authentication fix was applied.','']+record[2:]+['',
 '## Intended policy, scope and valid preconditions','',
 'The audit plan expects protected UI/ticket actions and sensitive internal agent operations to reject anonymous callers. Baseline endpoint_inventory.md classified the agent handlers as Public because that accurately described their source code. It was not a declaration that unrestricted internal-data access meets the intended security policy. This run validates the suspected gap rather than redefining a 200 response as secure.','',
 'Exactly four target requests were sent, one per declared route. Each used a newly constructed httpx client with trust_env=False and follow_redirects=False. Built requests had no Cookie, Authorization or Proxy-Authorization header; every cookie jar was empty before and after its request. No login, forged identity, invalid-token test, automatic redirect, extra health request or other target was used. The input sender audit_client is an ordinary declared string, not an impersonated privileged account.','',
 'The server bound its own 127.0.0.1 socket before startup; therefore the requests could not accidentally target another instance. Actual base URL: '+e['base_url']+'. The original FastAPI app/routes/functions executed without access-rule, score, dependency or response substitutions. Wrappers around the two agent functions only count/capture unchanged original returns. The owned server.started flag established startup before requests; all four actual HTTP responses establish runtime availability.','',
 'A temporary SQLite database contained only original project synthetic CSVs and four seeded accounts; no working-database rows were copied. Counts before requests: 80 articles, 500 historical tickets and four users. All four roles were present, but no role logged in. Original source/main-database hashes and the original private Phase1 backup were verified. After app startup, a separate private SQLite snapshot was made before the first request; integrity_check=ok and all ten table states matched. Its hash is `'+backup['sha256']+'`; private path/method are recorded in isolated_database_backup.json.','',
 'Valid form minimum lengths and the AgentMessage model were checked before requests. The knowledge-analysis endpoint declares no request body. Thus the observed behavior is not the result of deliberately malformed inputs, and no 422 schema failure is interpreted as authentication. Actual retrieval fields match the 427 eligible source records from the original CSVs.','',
 '## Exact requests and initial responses','',
 '| ID | Method / endpoint | Authentication sent | Initial response | Body bytes | Outcome |',
 '|---|---|---|---|---:|---|']
for row in request_rows:
 status=str(row['status'])+(' Location: '+row['location'] if row['location'] else '')
 notes.append(f"| {row['id']} | {row['method']} {row['endpoint']} | None | {status} | {row['body_bytes']} | {row['outcome']} |")
notes += ['',
 'A01: `GET /home`, no body. A02: `POST /tickets/create`, application/x-www-form-urlencoded with the following decoded fields:','',
 '~~~json',json.dumps(inputs['targets'][1]['body'],indent=2),'~~~','',
 'Both return 303 Location `/`, the login-page route in this app. Neither redirect is followed; both actual response bodies are empty, with no Set-Cookie header. Ten table fingerprints remain identical after each request. Ticket count remains 500, ticket row hash is unchanged and no agent log/citation/notification was created. These two checks PASS anonymous denial; they do not establish authenticated role or ownership behavior.','',
 'A03: `POST /agents/retrieval/search`, application/json:','',
 '~~~json',json.dumps(inputs['targets'][2]['body'],indent=2),'~~~','',
 'A04: `POST /agents/knowledge/analyze`, no body. A03 and A04 return application/json, status200 and no Location/Set-Cookie headers. Both original agent functions execute exactly once; HTTP JSON equals their captured original function results. There are zero redirect-history entries for all responses. A03 returns 3284 bytes and A04 returns 384 bytes. A01-A04/request.json preserve serialized bodies and actual header-absence checks; response.json preserves exact body_text plus its SHA256 and parsed JSON. response_body.txt is a convenient text copy with a final newline.','',
 '## Retrieval disclosure actually observed','',
 f"A03 returns decision {r['decision']}, best_score {r['best_score']!r}, and five full result items. Its success is an authentication failure regardless of ranking quality. This test does not re-score retrieval accuracy or generate a recommended answer.",'',
 '| Source | Type | Status | Score |',
 '|---|---|---|---:|']
for item in returned:
 notes.append(f"| {item['source_id']} | {item['source_type']} | {item['status']} | {item['score']:.10f} |")
notes += ['',
 'All seven original source fields in each result exactly match the seeded eligible record. The returned content below is synthetic audit evidence; no troubleshooting step was performed.','']
for item in returned:
 notes += ['### '+item['source_id']+' - '+item['title'],'','~~~text',item['content'],'~~~','']
notes += [
 'Observed disclosure: four historical problem descriptions and resolution notes, one approved internal KB body, titles/IDs/category/status/type/OS and ranking values. Historical Root cause labels are present but their values are empty; no nonempty root-cause details were demonstrated. The seeded articles have security_class=internal in the corpus metadata; that security_class field itself is not in this HTTP response. No credentials, owner identity, account profile, draft article, unresolved-ticket text or real-user data was returned in this request. The finding concerns unauthenticated access to this internal application data under the declared policy.','',
 '## Knowledge-health disclosure actually observed','',
 'A04 returns the following five rows plus `clusters: []`:','',
 '| Category | Tickets | Coverage | Gap |','|---|---:|---:|---|']
for row in health['health']:
 notes.append(f"| {row['category']} | {row['tickets']} | {row['coverage']:.3f} | {row['gap']} |")
notes += ['',
 'These are internal aggregate counts and knowledge-health indicators. With 500 seeded tickets, original analyze_knowledge_health() uses its >60 count-based coverage calculation and skips clustering at >=120. It does not expose individual ticket examples in this response. The health cache was absent before the request and present afterward: original analysis ran and populated only a process-local cache. No cached authenticated-session result was seeded into the test. Source code has other dataset-size paths; their possible outputs are not claimed as observed disclosures here.','',
 '## Technical cause and finding','',
 '**VULN-IR13-01 - Missing authentication exposes internal agent retrieval and knowledge analytics.**','',
 'The protected handlers call current_user_from_request(), which reads the access_token cookie and returns no user when absent. home() and create_ticket() then redirect to `/`. In contrast, retrieval_search() accepts AgentMessage plus get_session(); knowledge_analyze() accepts only get_session(). That dependency opens a database session and performs no identity check. Agent router creation and app.include_router(agents.router) add no authentication guard, and runtime metadata records zero app-router global dependencies and zero user middleware. Handler source excerpts/dependencies are in route_preflight.json.','',
 'AgentMessage validates five string metadata fields and a payload dictionary; none proves sender identity. In this ordinary request no privileged sender spoofing was required. The two sensitive handlers invoke search_knowledge()/analyze_knowledge_health() and return their complete results to the anonymous client. Front-end redirects therefore do not protect direct agent API operations. This is a demonstrated missing guard under intended policy, not merely an inference from a Public inventory label.','',
 'Source references: [agents.py](../../../../app/routes/agents.py) retrieval route lines24-26 and knowledge route38-40; [main.py](../../../../app/main.py) FastAPI construction20, router inclusion28 and home guard46; [auth.py](../../../../app/routes/auth.py) current_user_from_request26; [tickets.py](../../../../app/routes/tickets.py) create_ticket29; [database.py](../../../../app/database.py) get_session; [knowledge_intelligence_agent.py](../../../../app/agents/knowledge_intelligence_agent.py) analyze_knowledge_health. Line references describe the preserved original source, not a patch.','',
 '**Impact:** anonymous read access to the shown source content and internal aggregate analytics is demonstrated. Similar deployment with sensitive data, reachable by untrusted callers, could expose that data. No real-user disclosure, credential leak, account takeover, modification, denial of service or broad corpus extraction was tested or observed.','',
 '**Likelihood:** straightforward for a caller able to reach the service: a normal valid request needs no credential or user interaction. Each route was tested once; this establishes the local behavior, not an empirical population probability. The audit server listened only on loopback; external network reachability, deployment firewall/proxy controls and production exposure are untested.','',
 '**Severity/risk: Medium**, qualitative under the audit rubric. This is a meaningful authentication/confidentiality failure with easy invocation for a reachable caller, while demonstrated exposure is limited and all test data is synthetic. Higher severity, public exposure, real harm or a numeric CVSS score would require further evidence. One finding covers the common missing-authentication cause across two APIs; UI successes remain separate.','',
 '**Recommended mitigation, not applied:** require a shared verified active-user or authenticated service identity before invoking sensitive agent functions, then enforce explicit role/service permissions for each operation. Limit knowledge-health analysis to intended analysts/services and scope returned content to authorized needs. Reject absent/invalid credentials before expensive/data-reading work. Add authenticated-positive and missing/invalid-credential regression checks during authorized remediation. Do not treat payload sender strings, CORS, hidden UI links or an assumed external gateway as authentication. Role matrix and token probes are not performed in this case.','',
 '**Status:** confirmed locally; open; remediation not applied. Intended policy, reproduction, scope and severity are retained in finding.json and the vulnerability register. No application source, JWT setting, role or authentication configuration was changed.','',
 '## Integrity, runtime and limits','',
 'database_preflight.json and each A01-A04/database_after.json record only row counts and per-table hashes, not credential-bearing database rows. All ten table states match before/after each request. Final counts are unchanged: 80 articles, 500 tickets, four users; agentlog,category,notification,passwordresettoken,securityevent,solutionfeedback,ticketcitation remain empty. Seeded database main file and private snapshot are unchanged. Main application database and all baseline source files match original hashes; earlier audit evidence remains preserved. Main-file checks do not cover unrelated concurrent WAL writes by another instance.','',
 f"Worker start {e['started_at_utc']}; finish {e['finished_at_utc']} UTC. Parent elapsed {proc['elapsed_seconds']} seconds, exit 0, no timeout. Original retrieval function took {read('retrieval_function_result')['elapsed_seconds']} seconds; original knowledge analysis took {h['elapsed_seconds']} seconds. The recorded get_model() call took {e['model_load_call_seconds']} seconds, excluding prior import/startup time. Server stopped after capture.",'',
 'Configuration retained BM25 0.45 / semantic 0.55, HIGH 0.68 / UNCERTAIN 0.55, cached all-MiniLM-L6-v2 and one numerical-library thread. Groq was disabled and no chat call occurred. Authentication findings do not depend on LLM availability or answer generation.','',
 'Limits: four declared requests only; original synthetic CSV corpus; local development, no enterprise/public/production system or real users; no authenticated positive control in this case, alternate agent endpoint, role bypass, malformed credentials, ownership test, source poisoning, schema abuse, stress/load or DoS testing. Redirect destination is identified from preserved app source; redirects were deliberately not followed. HTTP JSON/text is actual response evidence, not a fabricated screenshot.','',
 '## Evidence and reproduction','',
 '| Files | Purpose |','|---|---|',
 '| inputs.json, expected_result.md | Exact request bodies, target limit and intended policy fixed before execution |',
 '| preconditions.json, corpus_preflight.json, eligible_records.json | Baseline source/main-DB/backup checks and actual synthetic retrieval corpus |',
 '| route_preflight.json | Actual original handler source/dependency/body metadata |',
 '| isolated_database_backup.json, database_preflight.json | Private consistent snapshot and nonsecret table fingerprints before requests |',
 '| A01-A04/request.json | Actual built bodies, absent-auth checks, fresh-client and redirect settings |',
 '| A01-A04/response.json, response_body.txt | Initial status/Location/body, byte count and original-body hash |',
 '| A01-A04/database_after.json, database_postflight.json | No ticket/persistent-table changes after each request and final snapshot check |',
 '| retrieval_function_result.json, knowledge_function_result.json | Original function outputs and health-cache state |',
 '| response_summary.json, execution.json, process_result.json, terminal_log.txt | Raw request counts, responses, timing, shutdown and integrity |',
 '| endpoint_results.json/CSV, disclosure_review.json, finding.json, review.json, evidence_integrity.json, notes.md | Later reviewed outcomes and confirmed scoped vulnerability |','',
 'Already executed once. This command creates a new synthetic database/evidence run, snapshots it, sends only the four requests and stops its server:','',
 '~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir13.py','~~~','',
 'The completed run used '+e['base_url']+'; that audit server is now stopped. Use the runner to reproduce its isolation instead of sending mutation requests to an unrelated localhost instance. Exact method/URL/body are saved per target. No credentials are required or included in these test requests.','',
 '**Conclusion:** IR-13 FAIL; two UI checks PASS and two anonymous agent-data responses FAIL. VULN-IR13-01 is confirmed at Medium severity within the local synthetic scope. Original capture statuses remain Unassessed for preservation; review.json provides the later verdict. IR-14 and IR-15 remain unexecuted; stop before IR-14.','']
notes=[line.replace(f'[{REL}/notes.md]({REL}/notes.md)','[notes.md](notes.md)') for line in notes]
write(RUN/'notes.md','\n'.join(notes))
progress='IR-13 failed unauthenticated agent access: UI guards passed, while two APIs returned internal synthetic data anonymously; VULN-IR13-01 is confirmed Medium. IR-14 and IR-15 remain Not run.'
for name,area in [('test_results.md','Authentication'),('test_plan.md','Authentication')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert 'IR-13 through IR-15 remain Not run.' in text
 text=text.replace('IR-13 through IR-15 remain Not run.',progress,1)
 text,count=re.subn(r'^\| IR-13 \|.*$',f'| IR-13 | {area} | Completed (local HTTP; synthetic) | [{REL}/notes.md]({REL}/notes.md) | FAIL (APIs); PASS (UI controls) | YES - VULN-IR13-01, Medium |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-13[^\n]*\n.*?(?=^## IR-14)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02 and IR-04 through IR-12 cases','the completed IR-01, IR-02 and IR-04 through IR-13 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-12/: actual case evidence, including isolated fixtures, grounding failures and separately labelled component boundary checks; IR-13 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-13/: actual case evidence, including retrieval checks and the confirmed unauthenticated agent-access finding; IR-14 and IR-15 remain reserved.')
text=text.replace('IR-13 through IR-15 remain Not run.',f'IR-13 failed: two agent APIs returned internal synthetic source/analytics data anonymously, while UI denial held. VULN-IR13-01 is confirmed Medium; see [{REL}/notes.md]({REL}/notes.md). IR-14 and IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8'); assert 'IR-13/ through IR-15/ contain placeholders only.' in text
text=text.replace('IR-13/ through IR-15/ contain placeholders only.',f'IR-13/{RUN.name}/ contains four actual anonymous HTTP requests: UI controls PASS, two agent endpoints FAIL with data returned. VULN-IR13-01 is confirmed Medium; requests, full responses, source matches and per-request table-integrity checks are saved. IR-14/ and IR-15/ contain placeholders only.')
write(path,text)
path=AUDIT/'vulnerability_register.md'; text=path.read_text(encoding='utf-8')
assert '## VULN-IR13-01' not in text
text=text.replace('No runtime-validated vulnerability entries have been created during Phase 1. This does not establish that the system is secure.','Phase 1 created no runtime-validated vulnerability entry. Subsequent IR-13 confirms VULN-IR13-01 (Medium): missing authentication on sensitive agent retrieval and knowledge-analysis endpoints. Earlier reliability observations retain their original classifications.',1)
entry=['## VULN-IR13-01 - Missing authentication on sensitive agent endpoints','']
for label,key in [('Vulnerability ID','vulnerability_id'),('Title','title'),('Related Test','related_test'),('Affected Component','affected_components'),('Description','description'),('Impact','impact'),('Likelihood','likelihood'),('Severity','severity'),('Risk Level','risk_level'),('Severity Justification','severity_justification'),('Technical Explanation','technical_explanation'),('Recommended Mitigation','recommended_mitigation'),('Status','status')]:
 value=finding[key]; value='; '.join(value) if isinstance(value,list) else value
 entry.append('- '+label+': '+value)
entry += [f'- Evidence: [{REL}/notes.md]({REL}/notes.md); A03/A04 request/response JSON and original function captures; all-table preservation checks; finding.json.', '- Scope: Four actual localhost requests with synthetic data. /home and /tickets/create correctly return 303 to login; two agent APIs return 200 and real seeded content. Historical root-cause values are empty; knowledge-health clusters/examples are absent. No real data, public exposure, persistent write, privilege escalation or DoS demonstrated.', '- Outcome: IR-13 FAIL; one common finding across two APIs. IR-14/IR-15 not executed.','']
write(path,text.rstrip()+'\n\n'+'\n'.join(entry))
path=AUDIT/'risk_matrix.md'; text=path.read_text(encoding='utf-8')
text=text.replace('No validated vulnerability is rated in Phase 1. The empty matrix is intentional.','Phase 1 produced no validated vulnerability rating. The following finding was subsequently confirmed by IR-13 on the local synthetic instance.',1)
needle='|---|---|---|---|---|'; assert text.count(needle)==1
row=f'| [VULN-IR13-01]({REL}/notes.md) - Missing agent API authentication | Anonymous source text and aggregate knowledge-health disclosure; no writes/real data observed | Easy for callers able to reach the service; local behavior tested once per endpoint, external reachability unknown | Medium (qualitative) | Require verified identity and route/service permissions; add authentication regression coverage |'
text=text.replace(needle,needle+'\n'+row,1)
text+='\n## IR-13 assessment\n\nBoth anonymous agent APIs returned 200 with internal synthetic data while UI controls denied access. One common missing-authentication cause is confirmed as VULN-IR13-01. Medium reflects a meaningful but limited demonstrated confidentiality/control failure and easy invocation by a reachable caller. The owned server bound only to loopback; no internet/production exposure, real-user breach, mutation, account takeover, stress test or numeric CVSS score is claimed. The knowledge response contained aggregates only, and all historical root-cause fields in retrieval were empty. No repair/fix applied.\n'
write(path,text)
additions={
 'viva_notes.md':'''## IR-13 observed result

I sent four valid requests with a new unauthenticated client for each, no cookies/authorization headers and no redirects followed. GET /home and POST /tickets/create returned 303 to the login route /, with empty bodies and no new ticket. POST /agents/retrieval/search returned 200 and five full source records; POST /agents/knowledge/analyze returned 200 and five aggregate rows. Both HTTP bodies matched the original agent function results. All ten table fingerprints stayed unchanged.

I recorded one Medium finding, VULN-IR13-01: the agent routes use get_session but no verified-user guard, while the UI checks current_user_from_request. Database sessions and AgentMessage sender fields do not authenticate a caller. The baseline Public label described missing enforcement; intended policy still requires protection. No privileged identity spoofing was needed.

The disclosure is limited to synthetic historical descriptions/resolutions, one KB body and aggregate analytics. Root-cause values were empty and clusters/examples absent. The server was localhost-only, so I do not claim an internet attack or real breach. Groq was disabled and never called. Recommend shared verified identity and explicit route permissions before agent work, followed by regression tests. No fix, role tests or IR-14 execution was performed.
''',
 'commands.md':f'''## IR-13 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir13.py
~~~

Already executed once. A rerun creates fresh evidence and a private synthetic database, verifies the recorded original backup, starts its own loopback server, snapshots all tables, and sends one request each to GET /home, POST /tickets/create, POST /agents/retrieval/search and POST /agents/knowledge/analyze. Fresh clients send no authentication and do not follow redirects. Valid nonsecret request bodies are saved in inputs.json and each A01-A04/request.json. Table hashes are checked after each request and the server stops afterward. It does not log in, change roles, test other endpoints or fix authentication. Read [{REL}/notes.md]({REL}/notes.md) for the confirmed FAIL/Medium finding. record_ir13.py derives the report without new requests and must not be rerun after recording.
''',
 'endpoint_inventory.md':f'''## IR-13 runtime addendum

The Phase 1 classifications above remain descriptions of original source enforcement. IR-13 now verifies four routes on an isolated original synthetic dataset. Anonymous GET /home and POST /tickets/create return 303 to / with no data or ticket creation. Anonymous POST /agents/retrieval/search and POST /agents/knowledge/analyze return 200 with internal synthetic source text and aggregate analytics. These Public-in-source agent routes FAIL the audit's intended protection policy, confirming VULN-IR13-01 (Medium). Other route classifications are not additional runtime test results. See [{REL}/notes.md]({REL}/notes.md); no application guard was changed.
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert addition.splitlines()[0] not in text
 write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before_hashes for name,before_hashes in prior.items())
assert all(sha(ROOT/name)==digest for name,digest in raw_before.items())
assert all(p.name=='.gitkeep' for i in (14,15) for p in (AUDIT/'evidence'/f'IR-{i:02d}').rglob('*') if p.is_file())
save('evidence_integrity',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'prior_evidence_directories_unchanged':list(prior),'prior_file_counts':{name:len(value) for name,value in prior.items()},'original_IR13_captures_unchanged':True,'raw_capture_sha256':raw_before,'source_files_match_baseline':True,'working_database_main_file_matches_baseline':True,'private_seeded_snapshot_unchanged':True,'IR14_and_IR15_unexecuted':True})
print('IR-13 FAIL recorded: UI controls PASS, agent API authentication FAIL; VULN-IR13-01 Medium confirmed. Raw/prior evidence and application/database preserved. Stopped before IR-14.')
