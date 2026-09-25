"""Review IR-15 saved captures only; no HTTP or application imports."""
from pathlib import Path
from datetime import datetime,timezone
import ast,copy,csv,hashlib,io,json,re,sqlite3
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'; RUN=AUDIT/'evidence/IR-15/run-20260923T023805163543Z'; REL=RUN.relative_to(AUDIT).as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name,folder=RUN): return json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
def save(name,value): write(RUN/(name+'.json'),json.dumps(value,indent=2,ensure_ascii=False))
def hashes(folder): return {p.relative_to(ROOT).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
def diffs(a,b,path=''):
 if type(a)!=type(b): return [path]
 if isinstance(a,dict):
  result=[]
  for k in sorted(set(a)|set(b)):
   p=path+'.'+k if path else k
   result+=diffs(a[k],b[k],p) if k in a and k in b else [p]
  return result
 if isinstance(a,list):
  if len(a)!=len(b): return [path]
  return [p for i,(x,y) in enumerate(zip(a,b)) for p in diffs(x,y,f'{path}[{i}]')]
 return [] if a==b else [path]
assert not (RUN/'review.json').exists(), 'Already reviewed; do not rerun writer'
prior={name:hashes(AUDIT/'evidence'/name) for name in ['baseline']+[f'IR-{i:02d}' for i in range(1,15)]}; raw_before=hashes(RUN)
e=read('execution'); proc=read('process_result'); inputs=read('inputs'); pre=read('preconditions'); before=read('database_preflight'); post=read('database_postflight'); scope=read('runtime_scope'); chosen=read('chosen_scope'); probe=read('full_app_import'); probe_process=read('full_app_import_process'); corpus=read('corpus_preflight'); schema=read('agent_message_schema')
assert proc['exit_code']==0 and not proc['timed_out'] and proc['mode']=='selected'
assert e['mode']=='selected' and e['status']=='Executed; awaiting scoped validation and provenance review' and e['server_started'] and e['server_stopped'] and not e['full_application_loaded']
assert (e['login_requests'],e['profile_requests'],e['documentation_requests'],e['target_requests'],e['retrieval_boundary_calls'],e['real_retrieval_calls'],e['solution_calls'],e['redirect_followups'])==(1,1,2,19,10,0,4,0)
assert e['llm']=={'configured_enabled':False,'attempts':2,'successful_returns':0,'failures':2}
assert all(proc[k] for k in ('source_files_unchanged','original_database_main_file_unchanged','prior_evidence_unchanged'))
assert all(sha(ROOT/p)==value for p,value in pre['prior_evidence_sha256'].items())
baseline=read('environment',AUDIT/'evidence/baseline'); assert all(sha(ROOT/p)==value for p,value in baseline['source_sha256'].items()) and sha(ROOT/'knowgap.db')==baseline['original_database_sha256']
original_backup=read('database_backup',AUDIT/'evidence/baseline'); assert sha(Path(original_backup['path']))==original_backup['backup_sha256']
assert probe_process['exit_code']==1 and not probe_process['timed_out'] and probe['HTTP_requests']==0 and not probe['server_started']
assert probe['error']['type']=='ImportError' and '_batched_linalg' in probe['error']['message'] and 'Application Control' in probe['error']['message']
assert not scope['full_application_loaded'] and not scope['full_agents_module_imported'] and scope['global_dependencies']==scope['custom_middleware']==scope['dependency_overrides']==0
assert chosen['mode']=='selected'
source=(ROOT/'app/routes/agents.py').read_text(encoding='utf-8'); tree=ast.parse(source)
for item in scope['selected_handlers']:
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==item['name'])
 assert hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()==item['ast_sha256'] and ast.get_source_segment(source,node)==item['source']
 assert [ast.get_source_segment(source,d) for d in node.decorator_list]==item['decorators']
assert scope['schema_source'].strip() in (ROOT/'app/schemas.py').read_text(encoding='utf-8') and scope['solution_component_source'].strip() in (ROOT/'app/agents/solution_agent.py').read_text(encoding='utf-8')
assert set(schema['required'])=={'message_id','request_id','sender','receiver','task','payload'} and schema['properties']['payload']['additionalProperties'] is True
assert all('maxLength' not in p and 'enum' not in p for p in schema['properties'].values())
assert post['all_tables_unchanged'] and post['private_snapshot_unchanged'] and post['synthetic_source_was_never_inserted'] and post['tables']==before['tables']
assert len(before['tables'])==10 and before['tables']['knowledgearticle']['row_count']==80 and before['tables']['ticket']['row_count']==500 and before['tables']['user']['row_count']==4
snapshot=read('isolated_database_backup'); assert snapshot['integrity_check']=='ok' and snapshot['outside_repository'] and snapshot['all_table_states_match'] and sha(Path(snapshot['path']))==snapshot['sha256']
assert corpus['synthetic_marker_source_absent'] and corpus['marker_text_absent'] and not corpus['synthetic_source_inserted'] and corpus['S00_source_titles_and_contents_match_current_seed']
# Read private database only; retain hashes/counts, never raw user rows in report/output.
with sqlite3.connect(Path(e['isolated_database']).as_uri()+'?mode=ro',uri=True) as con:
 con.execute('PRAGMA query_only=ON')
 for table,expected in post['tables'].items():
  assert re.fullmatch(r'[a-zA-Z0-9_]+',table)
  records=con.execute('SELECT * FROM "'+table+'" ORDER BY rowid').fetchall()
  assert len(records)==expected['row_count'] and hashlib.sha256(json.dumps(records,ensure_ascii=False,separators=(',',':'),default=str).encode()).hexdigest()==expected['rows_sha256']
 assert con.execute('SELECT count(*) FROM knowledgearticle WHERE doc_id=?',(inputs['synthetic_source']['source_id'],)).fetchone()[0]==0
 assert con.execute('SELECT count(*) FROM ticket WHERE ticket_code=?',(inputs['synthetic_source']['source_id'],)).fetchone()[0]==0
login=read('login'); profile=read('profile_control')
assert login['status']==303 and login['location']=='/home' and login['cookie_present'] and not login['credentials_recorded'] and login['redirect_history']==0
assert profile['status']==200 and profile['profile_form_present'] and profile['identity']['id']==corpus['logged_in_fixture_user_id'] and profile['identity']['stored_role']=='CUSTOMER' and profile['identity']['active'] and profile['redirect_history']==0
for ident in ('D01','D02'):
 doc=read(ident+'_documentation'); assert doc['status']==200 and doc['no_cookie_sent'] and doc['scope']=='selected'
assert read('D02_documentation')['body']['components']['schemas']['AgentMessage']==schema
expected={'R00':503,'R01':503,'R02':422,'R03':422,'R04':503,'R05':503,'R06':503,'R07':503,'R08':422,'R09':503,'P01':503,'P02':503,'P03':503,'S00':200,'S01':200,'S02':200,'S03':422,'S04':422,'S05':500}
classifications={
 'R00':('PASS','Valid envelope reaches selected handler boundary; actual retrieval blocked'),
 'R01':('FAIL','Empty string reaches search boundary; no required nonblank validation'),
 'R02':('PASS','Missing required payload rejected with 422 before downstream component'),
 'R03':('PASS','Missing required sender rejected with 422 before downstream component'),
 'R04':('FAIL','Object silently stringified and reaches search boundary'),
 'R05':('FAIL','List silently stringified and reaches search boundary'),
 'R06':('OBSERVATION','All 4000 characters reach boundary; no declared finite AgentMessage issue limit; no load/DoS result'),
 'R07':('PASS','Unicode text preserved at boundary; semantic retrieval untested'),
 'R08':('PASS','Malformed JSON rejected with 422 before downstream component'),
 'R09':('INCONCLUSIVE','Anonymous dispatch reaches boundary; full retrieval/data exposure blocked; existing IR13 finding unchanged'),
 'P01':('OBSERVATION','Sender claim ignored; same retrieval dispatch, no authenticated impersonation demonstrated'),
 'P02':('OBSERVATION','Receiver claim ignored; no admin task or role change demonstrated'),
 'P03':('OBSERVATION','Task claim ignored; no knowledge approval or role change demonstrated'),
 'S00':('PASS','Original solution component accepts saved genuine source control; not fresh retrieval'),
 'S01':('PASS','LOW synthetic control declines; escalation wording is not persistent escalation'),
 'S02':('FAIL','Only decision HIGH causes nonexistent draft zero-score source to be recommended as approved/validated'),
 'S03':('PASS','List retrieval rejected with controlled 422'),
 'S04':('PASS','Missing retrieval rejected with controlled 422'),
 'S05':('FAIL','Malformed nested item triggers original component KeyError and 500; response hides traceback'),
}
rows=[]; observations={}; responses={}; requests={}
for target in inputs['targets']:
 ident=target['id']; folder=RUN/ident; q=read('request',folder); r=read('response',folder); o=read('component_observations',folder); b=read('database_before',folder); a=read('database_after',folder)
 requests[ident]=q; responses[ident]=r; observations[ident]=o
 assert q['body']==target['body'] and q['path']==target['path'] and q['raw_body']==target['raw_body'] and r['status']==expected[ident]
 assert q['cookie_present']!=(ident=='R09') and not q['authorization_header_present'] and q['cookie_value']=='omitted' and not q['follow_redirects']
 assert r['redirect_history']==0 and not r['set_cookie_present'] and r['location'] is None
 assert len(r['body_text'].encode('utf-8'))==r['body_bytes'] and hashlib.sha256(r['body_text'].encode('utf-8')).hexdigest()==r['body_sha256']
 assert 'Traceback' not in r['body_text'] and 'File "' not in r['body_text']
 assert q['serialized_body']==target['raw_body'] if target['raw_body'] is not None else json.loads(q['serialized_body'])==target['body']
 assert a['unchanged_from_before_request'] and a['unchanged_from_seed'] and a['changed_tables']==[] and a['tables']==b['tables']==before['tables']
 assert not o['retrieval_backend_executed']
 if expected[ident]==503:
  assert r['audit_boundary_503'] and len(o['retrieval_boundary_calls'])==1 and not o['original_solution_calls'] and not o['original_llm_attempts']
  call=o['retrieval_boundary_calls'][0]; issue=target['body']['payload']['issue']
  assert call['query']==str(issue) and call['python_type']=='str' and call['character_length']==len(str(issue)) and not call['backend_executed']
  assert r['body_json']=={'detail':'AUDIT_IR15_BOUNDARY_ONLY: retrieval backend unavailable; no ranking executed'}
 elif expected[ident]==422:
  assert not o['retrieval_boundary_calls'] and not o['original_solution_calls'] and not o['original_llm_attempts']
  if ident in ('S03','S04'): assert r['body_json']=={'detail':'payload.retrieval must be an object'}
  else:
   error=r['body_json']['detail'][0]
   assert error['type']==('json_invalid' if ident=='R08' else 'missing')
   if ident!='R08': assert error['loc']==['body','payload' if ident=='R02' else 'sender']
 else:
  assert len(o['original_solution_calls'])==1 and not o['retrieval_boundary_calls']
  call=o['original_solution_calls'][0]
  assert call['query']==target['body']['payload']['query'] and call['retrieval_received']==target['body']['payload']['retrieval']
  if ident!='S05': assert call['result']==r['body_json']
  else: assert call['exception']=={'type':'KeyError','message':"'source_id'"} and r['body_text']=='Internal Server Error' and r['body_bytes']==21
 result,reason=classifications[ident]
 rows.append({'id':ident,'input_case':target['label'],'endpoint':q['path'],'http_status':r['status'],'audit_boundary_status':r['audit_boundary_503'],'authenticated_cookie_sent':q['cookie_present'],'retrieval_boundary_calls':len(o['retrieval_boundary_calls']),'actual_retrieval_calls':0,'solution_calls':len(o['original_solution_calls']),'database_unchanged':True,'outcome':result,'scope_reason':reason,'evidence':ident+'/response.json'})
base=requests['R00']['body']
for ident in ('R01','R04','R05','R06','R07'): assert diffs(base,requests[ident]['body'])==['payload.issue']
for ident,field in [('R02','payload'),('R03','sender'),('P01','sender'),('P02','receiver'),('P03','task')]: assert diffs(base,requests[ident]['body'])==[field]
assert requests['R09']['body']==base
assert diffs(requests['S01']['body'],requests['S02']['body'])==['payload.retrieval.decision']
low=responses['S01']['body_json']; high=responses['S02']['body_json']; fake=inputs['synthetic_source']
assert not low['can_recommend'] and low['confidence']=='LOW' and low['citations']==[] and low['source_id']==''
assert high['can_recommend'] and high['confidence']=='HIGH' and high['source_id']==fake['source_id'] and fake['content'] in high['message']
assert high['message']==f"Evidence source {fake['source_id']} | {fake['title']}\n{fake['content']}"
assert 'approved guidance' in high['explanation'] and 'validated for this workflow' in high['explanation'] and '0% relevance' in high['explanation']
assert len(high['citations'])==1 and high['citations'][0]['source_id']==fake['source_id'] and high['citations'][0]['hybrid_score']==0 and fake['status']=='draft'
assert observations['S01']['original_llm_attempts']==[] and observations['S05']['original_llm_attempts']==[]
for ident in ('S00','S02'):
 calls=observations[ident]['original_llm_attempts']; assert len(calls)==1 and calls[0]['result']=='exception' and calls[0]['type']=='RuntimeError' and not calls[0]['configured_enabled']
counts={name:sum(row['outcome']==name for row in rows) for name in ('PASS','FAIL','OBSERVATION','INCONCLUSIVE')}; assert counts=={'PASS':9,'FAIL':5,'OBSERVATION':4,'INCONCLUSIVE':1}
# All saved-evidence checks above are read-only. Reviewed artifacts begin below.
save('subcase_results',rows)
stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n'); writer.writeheader(); writer.writerows(rows); (RUN/'subcase_results.csv').write_text(stream.getvalue(),encoding='utf-8',newline='\n')
save('provenance_review',{'control':'S01','attempt':'S02','changed_fields':diffs(requests['S01']['body'],requests['S02']['body']),'shared_synthetic_source':fake,'source_absent_from_all_seeded_articles_and_tickets':True,'not_inserted_and_all_tables_unchanged':True,'LOW_can_recommend':low['can_recommend'],'HIGH_can_recommend':high['can_recommend'],'HIGH_actual_original_function_result':high,'disabled_llm_attempts_for_pair':1,'successful_provider_calls':0,'result':'FAIL: original solution component accepts caller-provided trust decision and nonexistent evidence','scope':'Original component executed via AST-selected original handler HTTP harness; full app and actual retrieval not run','not_claimed':['full application API exploitation','real customer delivery','persistent corpus poisoning or escalation','role escalation or authenticated agent impersonation','code execution, harmful actions, DoS or external exposure']})
finding={
 'vulnerability_id':'VULN-IR15-01',
 'title':'Caller-supplied retrieval decision and source text are treated as trusted evidence',
 'related_test':'IR-15, S01/S02 controlled provenance pair',
 'affected_components':['app/routes/agents.py: solution_recommend (exact handler AST in local audit HTTP composition)','app/agents/solution_agent.py: recommend_solution (original imported component)'],
 'description':'With one nonexistent synthetic source, status draft and zero scores held constant, changing only payload.retrieval.decision from LOW to HIGH changes can_recommend from false to true. The original component returns the caller marker/citation and describes the source as approved and validated without a corpus/provenance check.',
 'evidence':[REL+'/S01/request.json',REL+'/S01/response.json',REL+'/S02/request.json',REL+'/S02/response.json',REL+'/S02/component_observations.json',REL+'/provenance_review.json',REL+'/corpus_preflight.json'],
 'impact':'Recommendation integrity can be controlled by a caller able to supply retrieval metadata: untrusted text receives a fabricated trusted-evidence presentation. Only a harmless audit marker in a returned component/harness response was demonstrated. No persistent corpus poisoning, ticket creation/escalation, actual customer delivery, harmful system action or code execution was observed.',
 'likelihood':'Low effort at the tested component input boundary: one decision field suffices. Source shows the API handler forwards the caller object, but current full-application/API reachability is unverified because import is blocked. Broader deployment exposure, user consumption and prevalence are unknown.',
 'severity':'Medium',
 'risk_level':'Medium (qualitative; confirmed component scope)',
 'severity_justification':'Meaningful evidence-integrity/trust-boundary failure with a minimal controlled input change. Demonstrated impact is limited to returned advice/citation, so no High/Critical or CVSS score is assigned. Full-app exploitability and downstream effects remain unverified.',
 'technical_explanation':'AgentMessage.payload is Dict[str, Any]. solution_recommend checks only that retrieval is a dict and forwards it to recommend_solution. The latter gates on decision == HIGH and truthy items, then trusts source_id/title/content and labels them approved/validated. It performs no trusted corpus lookup, status verification or server-derived threshold/provenance check. Disabled Groq raises locally; the original fallback copies supplied evidence.',
 'recommended_mitigation':'Do not accept client declarations as retrieval proof. Obtain source content/status and confidence from a trusted server retrieval step bound to the request and verified caller/service. Resolve source identifiers against authorized approved/resolved records; reject nonexistent/ineligible sources; compute the decision server-side. Add typed nested payload validation and bounded input policy, plus verified API/service identity and operation permissions. Add LOW/HIGH forged-source regression controls during authorized remediation; schema validation alone does not establish provenance.',
 'status':'Confirmed in original component and selected-handler HTTP harness; open; remediation not applied; full-application exposure not reverified',
 'scope':'Owned localhost selected-handler harness, synthetic original corpus, existing disabled Groq configuration. Full app import blocked by Application Control on SciPy _batched_linalg. No real retrieval/embedding executed.',
 'separate_existing_finding':'VULN-IR13-01 remains confirmed Medium/open; this is a distinct evidence-trust failure, not a duplicate anonymous-data finding.',
}
save('finding',finding)
save('observations',[
 {'id':'OBS-IR15-01','title':'Incomplete nested payload validation','subcases':['R01','R04','R05','S05'],'outcome':'FAIL within schema/handler/component scope','actual':'Blank issue accepted; object/list converted with str; malformed HIGH item caused KeyError(source_id) and a 500 response. No HTTP traceback or persistent mutation.','security_classification':'Informational observation; no separate confirmed vulnerability or DoS claim','mitigation':'Typed operation-specific payloads; require nonblank text; validate nested source/item fields before component calls; return controlled 4xx.'},
 {'id':'OBS-IR15-02','title':'No finite issue-length contract in AgentMessage','subcases':['R06'],'outcome':'Design observation, not threshold violation','actual':'Exactly 4000 characters reached the observer intact; actual processing/ranking stopped. No maxLength for issue/envelope strings in captured schema.','security_classification':'Informational; no load/DoS behavior tested','mitigation':'Define and enforce a finite issue/body limit suited to the endpoint; this probe does not establish an existing 4000-character limit.'},
 {'id':'OBS-IR15-03','title':'Agent labels are ignored rather than verified protocol identity','subcases':['P01','P02','P03'],'outcome':'Protocol design observation','actual':'Changing sender, receiver or task independently still dispatched the same issue to the selected retrieval boundary. No alternate task, privileged identity or database action occurred.','security_classification':'Informational; not proof of authenticated impersonation or role escalation','mitigation':'Authenticate service/caller identity independently and bind permitted operations to routes; validate envelope labels for the intended protocol without treating strings as credentials.'},
])
save('review',{'test_id':'IR-15','test_name':'API Input Validation / Security','status':'Partially assessed','observed_outcome':'FAIL (component provenance and payload validation)','subcase_counts':counts,'full_application_and_actual_retrieval':'Blocked / Inconclusive: Application Control on SciPy _batched_linalg','runtime_scope':'AST-selected original HTTP handlers, original AgentMessage and original solution component; explicit retrieval observer stops with audit-generated 503','HTTP_requests':23,'target_requests':19,'target_response_counts':{'audit_503':10,'real_422':5,'real_200':3,'real_500':1},'new_finding':'VULN-IR15-01, Medium, confirmed component scope','existing_VULN_IR13_01':'Open; unchanged; no new full-app authentication retest','actual_retrieval_calls':0,'LLM_attempts_disabled':2,'successful_provider_calls':0,'all_database_tables_unchanged':True,'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'case_sequence':'IR-01 through IR-15 now have evidence; IR-03, IR-14 and IR-15 retain partial/inconclusive scope limits; no automatic remediation'})
record=[
 '## IR-15 - API Input Validation / Security','',
 '- Test ID: IR-15',
 '- Test Name: API Input Validation / Security',
 '- Test Objective: Check API payload validation and whether self-declared agent labels or caller-supplied retrieval metadata establish trusted identity/evidence.',
 '- Component Being Tested: Original AgentMessage schema, exact selected retrieval_search()/solution_recommend() handler ASTs/decorators, original recommend_solution() and disabled llm.chat(). Full app and real search_knowledge/embedding/ranking execution were blocked.',
 '- Input / Attack Scenario: Nineteen declared POSTs: valid retrieval envelope, blank issue, missing payload/sender, object/list issue, one 4000-character issue, Unicode, malformed JSON, anonymous valid request, three independent sender/receiver/task claims, saved genuine solution control, synthetic LOW/HIGH pair, retrieval list/missing retrieval, and one malformed nested item. Four controls: normal login, profile, /docs and /openapi.json.',
 '- Preconditions: Source/main DB/prior evidence and original private backup match baseline. Separate seeded database has 80 articles, 500 tickets and four users; private snapshot verified. Fake source AUDIT-IR15-NOT-IN-CORPUS/marker absent and never inserted. Groq already disabled. Scope/criteria fixed before HTTP.',
 '- Steps: Preserve failed full-app import; predeclare selected-handler fallback; compile unchanged function ASTs/decorators with original schema/solution; stop retrieval through explicit observer; start owned server, snapshot DB, login/profile controls, capture actual docs, send each bounded case once; record exact request/response, component calls and table hashes; stop server and review saved evidence.',
 '- Expected Behaviour: Invalid structures receive controlled 4xx before downstream work. Nonblank textual issue policy prevents silent object/list coercion. Caller HIGH and fabricated sources do not become trusted advice; role/agent identity is not established by labels. A finite input policy is evaluated without inventing a 4000-character current limit.',
 '- Actual Behaviour: Full import failed with Application Control blocking SciPy _batched_linalg, zero HTTP. Selected harness ran 23 HTTP requests: 19 target responses comprised ten labelled audit 503 stops, five real 422, three 200 and one 500. Required envelope/JSON validation held; blank/object/list issues reached the boundary. Only LOW-to-HIGH changed the synthetic pair: can_recommend false became true with nonexistent draft source, zero scores and approved/validated wording. Malformed item caused KeyError(source_id), response only Internal Server Error. No DB mutation or actual retrieval; two disabled LLM attempts, zero provider successes.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), subcase_results.json/CSV, finding.json, provenance_review.json, runtime_scope.json, full_app_import.json/log, R00-R09/P01-P03/S00-S05 request/response/component/table files, snapshot metadata and review.json.',
 '- Observation: Sparse typed envelope validation does not validate payload semantics or evidence provenance. Receiver/task changes did not execute privileged actions. R09 reached the observer without a cookie; actual anonymous retrieval/data exposure was not executed. S01 wording claims escalation but no persistent ticket/escalation occurred.',
 '- Outcome: Partially assessed: FAIL for observed component provenance/payload validation; 9 scoped PASS, 5 scoped FAIL, 4 observations, 1 Inconclusive. Full application, actual retrieval and fresh anonymous exposure remain Blocked / Inconclusive.',
 '- Vulnerability Identified: YES - VULN-IR15-01, Medium, caller-controlled evidence/decision trusted by original solution component. Input coercion and isolated 500 are separate robustness observations, not automatically vulnerabilities. IR-13 finding remains open.',
 '- Impact: Harmless untrusted text/citation returned as approved/validated advice; no database poisoning, real user delivery, ticket creation, harmful action, code execution or service-wide outage demonstrated.',
 '- Likelihood: One field change sufficed at tested component boundary. API forwarding is source-supported; full-app reachability and downstream user behavior are unverified.',
 '- Severity: Medium qualitative for demonstrated component evidence-integrity weakness. No High/Critical or numeric CVSS; informational treatment for separate validation/protocol design observations.',
 '- Technical Explanation: payload is Dict[str, Any]; retrieval_search casts issue with str() and ignores sender/receiver/task. solution_recommend checks retrieval is dict but not its nested shape/provenance. recommend_solution trusts decision HIGH plus nonempty items, then copies supplied evidence on disabled-provider fallback; no source lookup/status check or score recomputation.',
 '- Recommended Mitigation: Obtain evidence and decision from verified server-side retrieval bound to authenticated caller/service and authorized sources; reject nonexistent/draft sources. Define typed operation payloads, nonblank text/finite input limits and nested item validation with controlled 4xx. Add component and later full-app regression checks after authorized remediation. No fix applied.',
 '- Conclusion: Source-selected HTTP/schema tests and real solution calls demonstrate a scoped provenance failure while full integration remains blocked. All 15 audit IDs now have evidence, but partial cases are not complete/full-system PASS claims. Stop after IR-15.',
 '- Testing Limitations: Local synthetic data, exact selected handlers rather than imported full agents router; observer-generated 503 never treated as product ranking result; genuine S00 sources reused from IR-13 rather than newly retrieved; disabled provider; no external/public/university systems, real data, production, load/DoS, JWT attack, persistence or harmful-action tests.',
]
notes=[
 '# IR-15 - API Input Validation / Security','',
 '**Status: Partially assessed. Observed component provenance and payload validation FAIL. VULN-IR15-01 is confirmed at Medium severity within the original solution component/selected-handler HTTP scope. Full-application and actual retrieval verification remain Blocked / Inconclusive.**','',
 '## What executed and what remained blocked','',
 'A fresh import of app.main failed before server startup or any HTTP request. This attempt reports ImportError: DLL load failed while importing _batched_linalg: An Application Control policy has blocked this file. The saved stack passes through the retrieval dependencies into SciPy linalg. This differs from IR-14\'s recorded torch_python.dll error; both prior records remain unchanged. The current failure is an environment limitation, not attacker-induced denial of service. See [full_app_import.json](full_app_import.json) and [full_app_import_log.txt](full_app_import_log.txt).','',
 'The fallback is explicitly narrower than the IR-14 original-router harness. The full agents module itself imports retrieval dependencies. The audit therefore parsed app/routes/agents.py and compiled only the unchanged retrieval_search and solution_recommend function ASTs, including their original decorators. It bound those functions in a small FastAPI app with the original AgentMessage, get_session and recommend_solution component. It mounted the original auth router for login/profile controls. AST hashes and captured function text match baseline source; no application file or role guard was rewritten.','',
 'Actual retrieval was replaced by an explicit audit observer that records the query and raises a labelled 503: AUDIT_IR15_BOUNDARY_ONLY: retrieval backend unavailable; no ranking executed. It returned no invented sources/scores. Thus ten 503 responses are test stops, not application failures or authentic search results. They can show schema acceptance, str conversion and which handler was reached; they cannot show semantic accuracy, retrieval work, protected-data disclosure or downstream query handling. The real solution function did execute and its outputs/errors were captured separately.','',
 'No Windows control, DLL, installed package, source file or baseline configuration was changed. Groq was already disabled and checked before every payload sequence began. Two original llm.chat attempts raised locally; no provider call succeeded. Saved Swagger HTML and OpenAPI JSON are actual responses from this selected-handler test app; no browser assets or external documentation were fetched. They are not full-app Swagger captures or screenshots.','',
 '## Case record','',*record[2:],'',
 '## Actual subcase results','',
 'All rows describe this explicit selected-handler/schema/component scope. Audit 503 means the observer stopped retrieval.','',
 '| ID | Case | HTTP | Outcome | Observed scope/reason |','|---|---|---|---|---|',
 *[f"| {row['id']} | {row['input_case']} | {str(row['http_status'])+(' (audit stop)' if row['audit_boundary_status'] else '')} | {row['outcome']} | {row['scope_reason']} |" for row in rows],'',
 'There are 9 PASS, 5 FAIL, 4 observations and 1 Inconclusive among 19 targets. These counts are not an accuracy/security percentage: each row has a different check and scope. Four additional controls succeeded: normal login 303 /home with issued cookie, authenticated profile 200 resolving CUSTOMER user 1, GET /docs 200, GET /openapi.json 200. Only R09 omitted the cookie among target requests; none sent an Authorization header. Cookie/token/password values were not saved. No redirects were followed.','',
 '## Validation and protocol detail','',
 'The captured AgentMessage schema requires message_id, request_id, sender, receiver, task and an object payload. It leaves payload.additionalProperties=true, with no issue schema or string maximum lengths. R02 missing payload, R03 missing sender and R08 malformed JSON receive normal FastAPI 422 before downstream component calls. S03 retrieval list and S04 missing retrieval receive the handler\'s controlled 422 detail payload.retrieval must be an object. These are validation successes, not evidence of authentication.','',
 'R01 empty issue reaches the observer as a zero-length str. R04 object becomes a 69-character Python dictionary representation; R05 list becomes a 61-character Python list representation. This confirms the original handler\'s silent str() conversion, but actual retrieval/recommendation from those strings did not run. R06 delivers all 4000 characters to the boundary; absent a finite declared policy, this is a design observation rather than an invented length-limit violation or load/DoS result. R07 preserves the 44-character multilingual string exactly through JSON/schema/handler transport; embedding interpretation is untested.','',
 'P01 changes only sender to knowledge_intelligence_agent; P02 changes only receiver to admin; P03 changes only task to approve_knowledge. All still reach the same retrieval observer with the unchanged 57-character issue. The fields are ignored by this route; no approval/admin operation or stored identity change was demonstrated. Arbitrary labels are not authenticated agent identity, but acceptance alone is not proof of impersonation. R09 shows no-cookie dispatch at this selected boundary; full retrieval/data exposure remains Inconclusive here. VULN-IR13-01 stays open on its preserved earlier evidence.','',
 'S05 changes only the HIGH pair\'s items to [{}]. The original solution component raises KeyError(\'source_id\') before its LLM call. The HTTP response is a 21-byte Internal Server Error with status 500. The traceback exists in the private audit server log, not in the HTTP body. This fails the controlled-error expectation but does not prove trace disclosure, process termination, service-wide unavailability or DoS.','',
 '## Controlled evidence-provenance comparison','',
 'S00 is a separate positive solution control using the actual IR-13 retrieval response. Its source IDs/titles/content were checked against the fresh synthetic seed. This is reused genuine evidence, not a new retrieval run. S01/S02 form a separate fixed synthetic-input family. The only difference between those two requests is payload.retrieval.decision (LOW to HIGH), verified recursively from the saved bodies.','',
 '| Fixed input | Actual value |','|---|---|',
 '| source_id | AUDIT-IR15-NOT-IN-CORPUS |',
 '| title | IR15 synthetic provenance marker |',
 '| content | IR15_MARKER_ONLY: record this test observation; no system action is requested. |',
 '| status / source_type | draft / audit_fixture |',
 '| best_score, hybrid_score, bm25_score, semantic_score | 0.0 each |',
 '| source presence | Absent from all 80 KB articles and 500 tickets; never inserted |','',
 '| Output | S01 LOW control | S02 HIGH attempt |','|---|---|---|',
 '| HTTP | 200 | 200 |',
 '| can_recommend | false | true |',
 '| source_id | Empty | AUDIT-IR15-NOT-IN-CORPUS |',
 '| citations | Empty | One citation carrying the synthetic source, with zero scores |',
 '| recommendation text | Declines recommendation | Copies the caller marker as evidence |',
 '| explanation | Insufficient evidence | Calls the source approved guidance and validated; reports 0% relevance |',
 '| original disabled LLM attempts | 0 | 1 (local RuntimeError; fallback used) |',
 '| persistent change | None | None |','',
 'The HIGH response is not a model hallucination result: the original disabled-provider fallback copies the caller evidence, while fixed component wording falsely grants approval/validation. This is a trust-boundary failure because the caller can supply both the evidence and the flag that permits recommending it. It is distinct from an honest retrieval mismatch or merely choosing bad relevance weights. The test marker requests no harmful system action. No article, ticket, escalation, citation row or user-facing delivery was persisted. S01\'s template says escalated, but unchanged tables prove no actual escalation occurred in this direct call.','',
 '## Finding, severity and mitigation','',
 '**VULN-IR15-01 - '+finding['title']+'.** '+finding['status']+'.','',
 '**Impact:** '+finding['impact'],'',
 '**Likelihood:** '+finding['likelihood'],'',
 '**Severity:** Medium. '+finding['severity_justification'],'',
 '**Technical explanation:** '+finding['technical_explanation'],'',
 '**Recommended mitigation (not applied):** '+finding['recommended_mitigation'],'',
 'Source references: [schemas.py](../../../../app/schemas.py), [agent routes](../../../../app/routes/agents.py), [solution agent](../../../../app/agents/solution_agent.py), [LLM service](../../../../app/services/llm.py). [finding.json](finding.json) and [provenance_review.json](provenance_review.json) retain the exact evidence and scope. Separate [observations.json](observations.json) covers incomplete nested validation, absent length policy and ignored agent labels without automatically turning every failure into a vulnerability.','',
]
notes += [
 '## Exact input, evidence and reproduction','',
 'The valid retrieval control sends POST /agents/retrieval/search with this JSON body:','',
 '```json',json.dumps(requests['R00']['body'],indent=2,ensure_ascii=False),'```','',
 'The source-provenance pair sends POST /agents/solution/recommend. Its HIGH attempt is:','',
 '```json',json.dumps(requests['S02']['body'],indent=2,ensure_ascii=False),'```','',
 'S01 uses exactly that second body with decision LOW. It does not remove the synthetic item or alter any scores. The marker is deliberately harmless and was never written to the corpus. Exact remaining bodies, including the complete 4000-character string and Unicode input, are in [inputs.json](inputs.json) and each subcase/request.json. R08 sent the literal truncated JSON {"message_id": with application/json content type. This is the one deliberately invalid JSON encoding; the other altered inputs are syntactically valid JSON.','',
 '| Evidence | What it establishes |','|---|---|',
 '| inputs.json, expected_result.md, chosen_scope.json | Bounded cases, expected behavior and reduced scope declared before target requests |',
 '| preconditions.json, process_result.json | Baseline source/main database/private backup and prior-evidence preservation |',
 '| full_app_import.json, full_app_import_log.txt, full_app_import_process.json | Actual import error, zero full-app requests, no timeout |',
 '| runtime_scope.json, agent_message_schema.json | Original selected AST/schema/function captures, substituted retrieval stop and explicit limits |',
 '| login.json, profile_control.json/HTML | Normal CUSTOMER login and authenticated profile control; secrets omitted |',
 '| D01_documentation.json, D02_documentation.json | Actual selected-app Swagger HTML and OpenAPI JSON, fetched without browser assets |',
 '| corpus_preflight.json, isolated_database_backup.json, database_preflight.json | Synthetic seed, nonexistent marker check and consistent private pre-request snapshot |',
 '| R00-R09/P01-P03/S00-S05/request.json and response.json | Actual serialized input, cookie presence, HTTP status/body/byte count/hash |',
 '| Each subcase/component_observations.json | Actual boundary input, original solution return/exception and disabled LLM attempts |',
 '| Each subcase/database_before.json and database_after.json | Per-request table counts/hashes and absence of persistent changes |',
 '| database_postflight.json, all_component_observations.json, execution.json, terminal_log.txt | Final state, call counts, timestamps, server exception and shutdown |',
 '| subcase_results.json/CSV, provenance_review.json, observations.json | Later reviewed results and distinctions between trust failure, robustness and scope limits |',
 '| finding.json, review.json, evidence_integrity.json, notes.md | Scoped vulnerability, case verdict and immutable-capture verification |','',
 'Already executed once. To create a new isolated run after case authorization, use:','',
 '```powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir15.py','```','',
 'The runner verifies the original private Phase 1 backup, creates and snapshots a fresh synthetic database, checks full-app import, records the chosen scope, and sends only the 23 declared requests. It requires Groq to already be disabled before the payload sequence. If the full app imports, its original retrieval executes; if import is blocked, the explicitly labelled selected-handler mode stops retrieval at the observer. Review scope from that new run before drawing conclusions; results here do not predict a future run. It binds its own loopback server and stops it afterward. Do not replay these bodies against an unrelated local instance or an external host.','',
 f"The recorded audit instance was {e['base_url']}; its server is now stopped. The documentation path was {e['base_url']}/docs. Saved D01/D02 responses are the evidence; no browser screenshot was fabricated. Current app/main startup is not certified by the harness. The record_ir15.py helper reviews existing captures and must not be rerun after report generation.",'',
 '## Integrity and limitations','',
 'All ten tables matched their pre-request row counts and hashes after each of the 19 target requests and at the end. Final counts remained 80 knowledge articles, 500 tickets, four users and zero rows in the other seven tables. Read-only inspection of the private database verified those hashes and the absence of the fake source ID. No source or marker was inserted, and no citation/ticket/escalation row was created. The private SQLite snapshot passed integrity_check and retained its hash. It stays outside the repository because the database contains account credential hashes; those rows and credentials are never exported.','',
 f"Selected worker start: {e['started_at_utc']}; finish: {e['finished_at_utc']}. Worker elapsed: {proc['elapsed_seconds']} seconds, exit 0, no timeout. The earlier import probe took {probe_process['elapsed_seconds']} seconds and exited 1. The owned audit server stopped. These timings describe this bounded run, not a performance benchmark.",'',
 'All 44 baseline source-file hashes and the original working-database main-file hash match the baseline. Baseline and IR-01 through IR-14 captures are preserved. Working-main-file hashes do not cover unrelated concurrent WAL activity by another application process. The raw execution record remains Unassessed to preserve what was captured; review.json contains the later interpreted result. No application, authentication, ranking, threshold, OS policy or dependency fix was applied.','',
 'Limits: synthetic data, local development, one bounded input per subcase, selected source functions rather than full router/app import, no actual search/ranking/embedding in this run, no successful live LLM, no external systems or real users, no ownership/token attack, persistence, harmful actions or DoS. A 422 is payload validation, not authentication. A labelled audit 503 is an instrumentation stop, not secure product behavior. A 500 without traceback is not traceback disclosure. Ignored envelope labels are not proof of impersonation.','',
 '**Conclusion:** IR-15 is partially assessed with a demonstrated component provenance FAIL and a Medium finding, VULN-IR15-01. Nine subcases pass within their stated scope, five fail, four are observations and one is inconclusive; full-app and actual retrieval remain blocked. All 15 core case IDs now have evidence, with IR-03, IR-14 and IR-15 still carrying explicit partial limits. IR-13 remains open. Stop after IR-15; no bonus tests or remediation were performed.','',
]
notes=[line.replace(f'[{REL}/notes.md]({REL}/notes.md)','[notes.md](notes.md)') for line in notes]
write(RUN/'notes.md','\n'.join(notes))
progress='IR-15 is partially assessed: selected-handler/schema/component checks demonstrate VULN-IR15-01 (Medium), caller-supplied evidence trusted by the original solution component; full app and actual retrieval remain blocked. All 15 core IDs have evidence; IR-03, IR-14 and IR-15 retain partial scope limits.'
for name,area in [('test_results.md','API and agent communication'),('test_plan.md','API validation and agent protocol security')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert 'IR-15 remains Not run.' in text
 text=text.replace('IR-15 remains Not run.',progress,1)
 text,count=re.subn(r'^\| IR-15 \|.*$',f'| IR-15 | {area} | Partially assessed (selected handlers/components) | [{REL}/notes.md]({REL}/notes.md) | FAIL (provenance/validation); full app/retrieval Blocked | YES - VULN-IR15-01, Medium (component scope) |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-15[^\n]*\n.*\Z',lambda m:'\n'.join(record)+'\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('and the partially assessed IR-03 and IR-14 cases (IR-14 route checks pass; full-app startup blocked).','and the partially assessed IR-03, IR-14 and IR-15 cases. IR-14 route checks pass; IR-15 confirms a component evidence-trust failure; their full-app verification remains blocked.',1)
text=text.replace('- evidence/IR-01/ through evidence/IR-14/: actual case evidence, including retrieval checks, the confirmed unauthenticated agent-access finding, and scoped IR-14 role checks with a preserved full-app startup blocker; IR-15 remains reserved.','- evidence/IR-01/ through evidence/IR-15/: actual case evidence, including retrieval checks, missing agent authentication, scoped role checks and a confirmed component evidence-trust failure; partial scope and startup limitations remain explicit.',1)
text=text.replace('IR-15 remains Not run.',progress+f' See [{REL}/notes.md]({REL}/notes.md).',1)
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8'); assert 'IR-15/ contains a placeholder only.' in text
text=text.replace('IR-15/ contains a placeholder only.',f'IR-15/{RUN.name}/ records 23 HTTP requests (19 subcases and four controls) after a preserved full-app import failure: 9 scoped PASS, 5 FAIL, 4 observations and 1 Inconclusive. VULN-IR15-01 is confirmed Medium in the original solution component: caller HIGH promotes a nonexistent draft zero-score source to approved/validated advice. Ten labelled audit 503 stops did not execute retrieval. Full-app/real-retrieval scope remains blocked; all tables are unchanged.',1)
write(path,text)
path=AUDIT/'vulnerability_register.md'; text=path.read_text(encoding='utf-8'); assert '## VULN-IR15-01' not in text
text=text.replace('Earlier reliability observations retain their original classifications.','IR-15 additionally confirms VULN-IR15-01 (Medium) within the original solution component/selected-handler HTTP scope: caller-controlled retrieval evidence is treated as approved and validated. Full-app exposure remains unverified for IR-15. Earlier reliability observations retain their original classifications.',1)
entry=['## VULN-IR15-01 - '+finding['title'],'']
for label,key in [('Vulnerability ID','vulnerability_id'),('Title','title'),('Related Test','related_test'),('Affected Component','affected_components'),('Description','description'),('Impact','impact'),('Likelihood','likelihood'),('Severity','severity'),('Risk Level','risk_level'),('Severity Justification','severity_justification'),('Technical Explanation','technical_explanation'),('Recommended Mitigation','recommended_mitigation'),('Status','status'),('Scope','scope')]:
 value=finding[key]; value='; '.join(value) if isinstance(value,list) else value; entry.append('- '+label+': '+value)
entry += [f'- Evidence: [{REL}/notes.md]({REL}/notes.md); S01/S02 request/response and component observations, provenance_review.json, source-absence and table-hash checks, finding.json.', '- Distinction: VULN-IR13-01 remains open; that earlier finding concerns missing authentication/data disclosure. IR-15 demonstrates a separate evidence-integrity failure with a normal CUSTOMER cookie; it does not establish that the agent endpoint validates that cookie.', '- Other IR-15 results: Required envelope/JSON/container validation passes. Empty/object/list issue handling and malformed nested item 500 are informational robustness observations; ignored labels and absent length policy are design observations. None is automatically a new vulnerability or DoS finding. Full application/real retrieval is blocked, and observer 503 responses are not application results.', '- Mitigation status: Recommendations only. No code, configuration, dependency or Windows policy changes; no bonus tests or further remediation executed.','']
write(path,text.rstrip()+'\n\n'+'\n'.join(entry))
path=AUDIT/'risk_matrix.md'; text=path.read_text(encoding='utf-8')
text=text.replace('The following finding was subsequently confirmed by IR-13 on the local synthetic instance.','IR-13 subsequently confirmed missing API authentication on the local synthetic instance. IR-15 confirms a distinct evidence-trust failure in the original solution component/selected-handler HTTP scope, with full-app exposure unverified.',1)
lines=text.splitlines(); index=next(i for i,line in enumerate(lines) if line.startswith('| [VULN-IR13-01]'))
lines.insert(index+1,f'| [VULN-IR15-01]({REL}/notes.md) - Caller-controlled evidence trusted | Nonexistent draft source and harmless caller text returned as approved/validated advice; no persistence or real delivery | One field at tested component input; full-app reachability and downstream use unverified | Medium (qualitative; confirmed component scope) | Use trusted server retrieval, resolve authorized eligible sources and derive decision server-side; validate payloads and service identity |')
write(path,'\n'.join(lines)+'\n\n## IR-15 assessment\n\nThe S01/S02 pair differs only in LOW versus HIGH. The original solution component accepts the nonexistent draft source with zero scores when HIGH is supplied, copies the harmless marker and claims approval/validation. This supports one Medium component evidence-integrity finding. It does not establish full-app exploitation, corpus poisoning, customer delivery, harmful execution or DoS. Full import was blocked by Windows Application Control; actual retrieval was stopped by explicit audit instrumentation. Other validation and metadata observations retain Informational treatment. VULN-IR13-01 remains unchanged and open.\n')
additions={
 'commands.md':f'''## IR-15 reproduction after explicit case authorization

```powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir15.py
```

The existing run has already executed; no requests were repeated to finish its review. A new invocation creates a new evidence directory and private seeded database, verifies the recorded original backup and makes a consistent snapshot before requests. It first attempts full-app import. The saved attempt was blocked by Windows Application Control while importing SciPy _batched_linalg, so it explicitly selected exact source-handler functions with the original schema/solution component and an audit retrieval observer. Ten 503 responses were deliberate stops with no ranking, not product behavior.

The declared limit is 19 target POSTs plus one login, one profile and GET /docs and /openapi.json (23 HTTP total). Groq must already be disabled, and no redirects are followed. Exact inputs and harmless source marker are saved in [{REL}/inputs.json]({REL}/inputs.json). Full result and scope: [{REL}/notes.md]({REL}/notes.md). The owned server is stopped. Saved Swagger/OpenAPI responses belong to the selected-handler app; they do not certify full-app startup or depict browser screenshots. Do not send these bodies to unrelated/public systems.

```powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\record_ir15.py
```

The second command only generates the reviewed report from saved captures; it sends no HTTP. It is a one-time writer and must not be rerun after review.json exists. No dependency repair, OS policy workaround, bonus test or application mitigation has been executed.
''',
 'endpoint_inventory.md':f'''## IR-15 runtime addendum

Full app import failed on SciPy _batched_linalg under Windows Application Control. The following results come from exact AST-selected original handler functions in an audit HTTP app with the original AgentMessage and recommend_solution component. The full agents router was not imported. Actual retrieval stopped at an explicitly substituted observer.

| Endpoint | Method | Observed validation | Authentication/protocol evidence | Scope limit |
|---|---|---|---|---|
| /agents/retrieval/search | POST | Missing payload/sender and malformed JSON: 422; empty/object/list issues accepted or stringified; all 4000 characters and Unicode preserved at boundary | No-cookie request reaches observer; sender/receiver/task changes leave dispatch unchanged | Observer returns audit 503; no actual ranking/data disclosure or impersonation demonstrated |
| /agents/solution/recommend | POST | Missing/non-object retrieval: 422; malformed nested item: plain 500; synthetic HIGH accepted and recommended | Caller decision promotes nonexistent draft zero-score source into approved/validated advice; VULN-IR15-01 Medium in original component scope | Normal CUSTOMER cookie sent; no demonstrated endpoint verification of it; no full-app exposure or persistence claim |
| /docs and /openapi.json | GET | Actual documentation responses: 200 | No cookie required in audit app | These show selected-app schema only, not full application routes |

VULN-IR13-01 remains open on its earlier original-app evidence. Validation responses do not prove authentication, and client envelope labels do not authenticate a service. No route classification or baseline source was altered. See [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':f'''## IR-15 observed result

**What did you test?** I assessed required fields, query types, bounded length, Unicode, malformed JSON, no-cookie dispatch, agent labels and caller-supplied retrieval evidence. Nineteen target requests plus four controls were captured.

**What was the key finding?** VULN-IR15-01 is a Medium evidence-integrity weakness in the original solution component. I held a nonexistent source, draft status and zero scores constant. Changing only the caller decision from LOW to HIGH changed can_recommend from false to true, copied the harmless audit marker, and described the source as approved and validated.

**Why is this different from IR-13?** IR-13 is missing authentication and anonymous data disclosure. IR-15 is a separate trust mistake: the caller can supply both evidence and the flag that allows recommending it. Adding login alone would not verify that the supplied evidence is a real, eligible source. I sent a normal CUSTOMER cookie, but did not claim that the agent handler verified it.

**Was this a model hallucination?** No live model output was used. Groq was disabled; two original chat attempts raised locally. The normal fallback copied supplied text, while fixed explanation text granted unsupported approval and validation. This is an observed component trust failure, not a claim that an LLM invented these facts.

**Why only Medium?** A single field controlled recommendation integrity in the tested component, but only a harmless marker in a response was demonstrated. Full-app exposure, real-user delivery, persistent poisoning and harmful actions were not established. The severity reflects that limited but meaningful impact.

**What validation worked?** Missing required payload/sender and malformed JSON were rejected with 422. Missing or non-object retrieval was also rejected with 422. Unicode survived transport. These successes do not prove authentication or semantic search quality.

**What validation failed?** Empty issues were accepted and object/list issues were converted to strings. An empty nested source object raised KeyError and produced a plain 500. No HTTP traceback was exposed. The single 4000-character probe showed no finite declared issue limit, but did not demonstrate overload or DoS.

**Did forged agent names grant privileges?** Changing sender, receiver or task still dispatched the same retrieval handler; no admin action or authenticated impersonation was shown. Labels were ignored rather than established as trusted identity.

**What could not be tested?** Full app import was blocked by Windows Application Control on a SciPy dependency. I preserved the failure and tested exact selected handler functions plus the original schema/solution component. Ten 503 responses were deliberately raised by an audit observer before actual retrieval. They cannot establish real search behavior, access protection or new data exposure. The documentation captures are from that selected app, not full-app Swagger.

**How did you verify integrity?** Every request had before/after table fingerprints. All ten tables matched the private pre-request snapshot, and the nonexistent source was never inserted. Source files, original database and earlier evidence remained unchanged. No application repair was applied.

**What mitigation would you recommend?** Derive the decision and evidence from trusted server retrieval, bind it to the verified caller/request, and resolve source IDs against authorized approved or resolved records. Reject fabricated/draft sources. Add typed nested payloads, nonblank text and explicit finite limits. Authenticate services independently of envelope strings. Test the forged-source pair again during authorized remediation, then complete full-app verification in a working environment.

Evidence: [{REL}/notes.md]({REL}/notes.md). All 15 core IDs now have evidence; IR-03, IR-14 and IR-15 retain their partial limitations. The two formal findings remain open. No bonus tests or remediation followed this case.
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8'); assert addition.splitlines()[0] not in text; write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==value for name,value in prior.items())
assert all(sha(ROOT/name)==value for name,value in raw_before.items())
save('evidence_integrity',{'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'prior_evidence_directories_unchanged':list(prior),'prior_file_counts':{name:len(value) for name,value in prior.items()},'original_IR15_captures_unchanged':True,'raw_capture_sha256':raw_before,'source_files_match_baseline':True,'working_database_main_file_matches_baseline':True,'private_seeded_snapshot_unchanged':True,'private_snapshot_path':snapshot['path'],'private_snapshot_sha256':snapshot['sha256'],'review_uses_saved_evidence_only':True,'new_HTTP_requests_during_review':0,'case_sequence':'Stop after IR-15; no bonus tests or remediation'})
print('IR-15 recorded: partially assessed; observed component provenance FAIL, VULN-IR15-01 Medium. 9 scoped PASS, 5 FAIL, 4 observations, 1 Inconclusive; full app and actual retrieval blocked. Raw/prior evidence preserved; no new HTTP. Stop after IR-15.')
