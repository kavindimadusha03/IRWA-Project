"""Record IR-08 fixture formatting results while preserving original evidence."""
from pathlib import Path
from datetime import datetime, timezone
import csv, hashlib, io, json, math, re
ROOT=Path(__file__).resolve().parents[2]; AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence/IR-08/run-20260922T132754058395Z'; REL=RUN.relative_to(AUDIT).as_posix()
NAMES=('lowercase','uppercase','prefix','punctuation','quoted'); CODE='0x00000124'; FID='AUDIT-IR08-EXACT-001'
def read(name,folder=RUN): return json.loads((folder/name).read_text(encoding='utf-8'))
def write(path,text): path.write_text(text.rstrip()+'\n',encoding='utf-8')
def hashes(folder): return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
prior={name:hashes(AUDIT/'evidence'/name) for name in ('baseline','IR-01','IR-02','IR-03','IR-04','IR-05','IR-06','IR-07')}; raw_before=hashes(RUN)
process=read('process_result.json'); fixture=read('fixture.json')['fixture']; original=read('source_preflight.json')
assert process['ticket_requests']==5 and len(process['subcases'])==5 and process['source_files_unchanged'] and process['original_database_main_file_unchanged']
assert read('preconditions.json')['private_phase1_backup_verified']
assert original['approved_exact_code_count_in_original']==original['eligible_resolved_exact_code_count_in_original']==0
cases={name:{key:read(key+'.json',RUN/name) for key in ('input','execution','analysis','query_preprocessing','token_code_preflight','eligible_corpus','hybrid_before_trust','retrieval','solution','ticket','fixture_preflight','process_result','support_queue_check')} for name in NAMES}
base=cases['lowercase']; summaries=[]; diagnostics=[]
for name,case in cases.items():
 e=case['execution']; a=case['analysis']; n=case['query_preprocessing']; tok=case['token_code_preflight']; c=case['eligible_corpus']; r=case['retrieval']; s=case['solution']; t=case['ticket']; p=case['process_result']; q=case['support_queue_check']
 assert e['ticket_requests']==1 and e['http']['ticket_page']==200 and e['http']['ticket_create']['status']==303 and e['server_stopped']
 assert p['process_exit_code']==0 and not p['timed_out'] and p['source_files_unchanged'] and p['original_database_main_file_unchanged']
 assert e['configuration']==base['execution']['configuration'] and not e['llm']['configured_enabled'] and e['llm']['successful_chat_returns']==0
 assert c['eligible_record_count']==428 and c['matches_CSV_plus_declared_fixture_in_all_retrieval_fields']
 assert c['eligible_corpus_sha256']==base['eligible_corpus']['eligible_corpus_sha256']
 assert case['fixture_preflight']['fixture']==fixture and case['fixture_preflight']['isolation_verified']
 assert len(c['eligible_exact_code_records'])==1 and c['eligible_exact_code_records'][0]['source_id']==FID
 assert a['canonical_issue']==t['canonical_issue']==t['description']==case['input']['description']
 assert tok['extracted_error_codes']==n['original_query_error_codes']==n['normalized_query_error_codes']==[CODE]
 assert tok['tokens'].count(CODE)==n['normalized_query_tokens'].count(CODE)==1
 assert n['normalized_query']==base['query_preprocessing']['normalized_query']
 assert r['items']==base['retrieval']['items'] and s==base['solution']
 assert r['items'][0]['source_id']==FID and [i['source_id'] for i in r['items'] if i['exact_error_match']]==[FID]
 assert r['decision']=='HIGH' and t['status']=='SOLUTION_PROPOSED' and t['approval_status']=='PENDING'
 expected='\n\n'.join(f"Evidence source {i['source_id']} | {i['title']}\n{i['content']}" for i in r['items'][:3])
 assert s['message']==t['recommended_solution']==expected
 assert q['page_status']==200 and not q['ticket_resolve_form_present'] and not q['ticket_code_present']
 assert a['entities']['error_code']==(None if name=='uppercase' else CODE)
 residuals=[]
 for item in case['hybrid_before_trust']:
  residual=item['hybrid_score']-.45*item['bm25_score']-.55*item['semantic_score']; bonus=.35 if item['source_id']==FID else 0.0
  assert math.isclose(residual,bonus,abs_tol=1e-10)
  residuals.append({'source_id':item['source_id'],'exact_error_match':item['exact_error_match'],'raw_hybrid':item['hybrid_score'],'observed_bonus_residual':residual,'expected_bonus':bonus,'check':'PASS'})
 diagnostics.append({'case':name,'rows':residuals})
 summaries.append({'case':name,'variant':case['input']['variant'],'description':case['input']['description'],'characters':case['input']['characters'],'canonical_issue':a['canonical_issue'],'normalized_query':n['normalized_query'],'retrieval_code_identity':CODE,'entity_error_code':a['entities']['error_code'],'entity_check':'FAIL' if name=='uppercase' else 'PASS','retrieval_outcome':'PASS','fixture_rank':1,'fixture_exact_error_match':True,'best_score':r['best_score'],'decision':r['decision'],'ranked_source_ids':[i['source_id'] for i in r['items']],'cited_source_ids':[i['source_id'] for i in s['citations']],'rankings_scores_flags_and_solution_equal_lowercase':True,'eligible_corpus_sha256':c['eligible_corpus_sha256'],'status':t['status'],'approval':t['approval_status'],'endpoint':e['endpoint'],'process_seconds':p['elapsed_seconds']})
comparison={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-08','primary_retrieval_outcome':'PASS','auxiliary_entity_outcome':'FAIL (uppercase only)','fixture_scope':'Synthetic lookup control only; not real troubleshooting validation','cases':summaries}
write(RUN/'comparison.json',json.dumps(comparison,indent=2))
write(RUN/'exact_boost_diagnostics.json',json.dumps({'method':'Arithmetic residual from actual hybrid returns; no alternate search or ablation','cases':diagnostics},indent=2))
output=io.StringIO(newline=''); fields=['case','variant','description','characters','retrieval_code_identity','entity_error_code','entity_check','retrieval_outcome','fixture_rank','fixture_exact_error_match','best_score','decision','ranked_source_ids','cited_source_ids']
w=csv.DictWriter(output,fieldnames=fields,lineterminator="\n"); w.writeheader()
for row in summaries: w.writerow({k:json.dumps(row[k]) if isinstance(row[k],list) else row[k] for k in fields})
write(RUN/'comparison.csv',output.getvalue())
review={'review_recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-08','status':'Completed (isolated fixture; fallback mode)','outcome':'PASS (primary retrieval formatting); FAIL (auxiliary uppercase entity check)','primary_retrieval_outcome':'PASS','auxiliary_entity_outcome':'FAIL','vulnerability_identified':'NO demonstrated security vulnerability','criteria':[
 {'name':'Five requests complete through same path','outcome':'PASS','evidence':'One ticket per variant; normal login; five result pages 200'},
 {'name':'Code identity preserved in retrieval preprocessing','outcome':'PASS','evidence':'All five normalize to the same string; one intact code token and same extracted code'},
 {'name':'Exact fixture retained with correct flags and bonus','outcome':'PASS','evidence':'Fixture first, exact=true, +0.35 residual; other returned records false/zero'},
 {'name':'No formatting-induced unsupported/confident transition','outcome':'PASS','evidence':'Complete rankings and solution objects identical across five forms'},
 {'name':'Auxiliary ticket entity extraction consistent','outcome':'FAIL','evidence':'Only uppercase analysis.entities.error_code is null'}],
 'observations':['OBS-IR08-01: uppercase entity correctness defect','OBS-IR03-01 applicability overstatement recurs; fixture caveat preserved','OBS-IR05-02 recurs: 144% UI / 100% explanation'],
 'security_assessment':'No observed access/approval bypass, disclosure, executed repair or exploitation. Entity failure did not alter this retrieval path; no formal VULN entry.',
 'severity':'Informational security observation; no vulnerability severity assigned',
 'limitations':['Synthetic control approval is metadata, not real repair validation','IR-03 original-corpus result remains Inconclusive','Generic historical repairs remain unverified for the stated code','Groq disabled in all cases','Only five planned formats; no other codes/boundaries tested','IR-09 through IR-15 unexecuted']}
write(RUN/'review.json',json.dumps(review,indent=2))
r=base['retrieval']; s=base['solution']; raw={i['source_id']:i for i in base['hybrid_before_trust']}
notes=['# IR-08 - Error-Code Formatting Variations','',
'**Outcome: PASS for primary retrieval formatting on an isolated fixture; FAIL for the auxiliary uppercase entity check.** All five variants yielded identical normalized queries, rankings, scores, flags and fallback answers. Uppercase 0X alone was missing from the analysis entity field. No security vulnerability was demonstrated.','',
'## Objective and exact input','',
'Assess case and punctuation tolerance without changing the error-code identity or introducing a formatting-driven unsupported confident answer. All tickets use title `Windows blue screen report` and sentence template `Windows blue screen error {variant}`.','',
'| Subcase | Exact submitted description | Characters |','|---|---|---:|']
for row in summaries: notes.append(f"| {row['case']} | `{row['description']}` | {row['characters']} |")
notes += ['', 'The prefix variant intentionally produces `error error:` by inserting the whole specified variant into the fixed sentence. All inputs exceed route minimum length and fit below the 180-character canonical limit; masking/truncation changed none. Exact input JSON/text is saved before requests.','',
'## Source prerequisite and controlled fixture','',
'The unchanged original corpus contains zero approved exact-code articles and zero eligible resolved exact-code tickets. Four matching historical tickets are Open without resolution and excluded. IR-03 therefore remains Inconclusive; its evidence was not edited.','',
'The IR-08 plan explicitly permits a labelled isolated fixture. The same article was added to each of five fresh temporary databases containing the original synthetic CSV data. Each actual retrieval corpus has 428 eligible records: the original 427 plus this one fixture. No working-database row or project CSV was modified.','',
'| Fixture field | Value |','|---|---|',f"| Source ID | {fixture['doc_id']} |",f"| Title | {fixture['title']} |",f"| Category | {fixture['category']} |",'| Status / type | approved / internal_kb |','| Authoritative / OS | false / Any |','| Author | IR-08 synthetic audit fixture |','| Created / updated | 2026-09-22, fixed across copies |','',
f"> {fixture['content']}",'',
'**Approved is synthetic fixture metadata, not independent approval or verification of a real diagnosis/repair.** This case tests lookup of a code-reference control; it does not repair the missing real knowledge in IR-03. Adding a document changes the corpus and normalization, so IR-08 scores are not a direct comparison with original-corpus IR-03 scores.','',
f"All five corpus hashes: `{base['eligible_corpus']['eligible_corpus_sha256']}`. All seven retrieval fields match the original CSV-derived records plus the declared fixture.",'',
'## Prior rules, prerequisites and steps','',
'- Primary PASS: all five requests succeed, code identity survives actual retrieval preprocessing, the exact fixture remains eligible/top-k with correct flags, and no formatting-induced unsupported confident transition occurs.',
'- Primary FAIL: valid formatting variation loses code identity/exact-source relevance, produces wrong flags, crashes or introduces an unsupported confident recommendation. Score changes alone would not fail retained relevance.',
'- Auxiliary entity check: all equivalent forms should populate entities.error_code consistently after normalization; assess separately because retrieval does not consume this field.',
'- Verify +0.35 from original raw-score components; no extra search, ablation or altered-score experiment. Inspect generic advice even when formatting parity passes.',
'- Missing environment/backup/login/corpus prerequisites would mean Not ready/Inconclusive. FAIL does not automatically mean vulnerability. These criteria were saved in expected_result.md before execution.','',
'Existing private Phase 1 backup verified by checksum; application/data/evaluation/test hashes unchanged. Each database has 80 CSV articles plus one fixture and 500 historical tickets. Active synthetic CUSTOMER/IT_SUPPORT users logged in normally. Credentials/cookies/tokens are omitted.','',
'Configuration: cached all-MiniLM-L6-v2, BM25/semantic 0.45/0.55, HIGH=0.68, UNCERTAIN=0.55, top-k=5 and one numerical-library thread. Groq model setting remains llama-3.1-8b-instant; Groq disabled in all five.','',
'1. Saved exact inputs, source gap, fixture and criteria.',
'2. For each variant, verified the temporary DB path, seeded the original corpus plus fixture and checked stored fields.',
'3. Started the unchanged app on an owned loopback socket, logged in as CUSTOMER and submitted once.',
'4. Observed original analysis, normalization, corpus/ranking and solution outputs without changing their arguments or results; saved ticket/citations and actual customer HTML.',
'5. Logged in as IT_SUPPORT, read the queue, stopped the server and verified source/database hashes.',
'6. Compared all five original outputs. No approval, rejection, resolution, manual escalation or recommended repair was executed.','',
'Reproduction command (already executed; a rerun creates new evidence and five temporary databases):','',
'~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir08.py','~~~','',
'The documented backup command is `python -B audit/scripts/collect_baseline.py backup`, using a read-only SQLite source and private temporary backup. This run verified the existing backup.','',
'Each sequential server used POST http://127.0.0.1:8001/tickets/create and GET /tickets/501. TCK-00501 belongs to a different isolated DB in each run. All five: health 200, CUSTOMER login 303 to /home, home 200, create 303, ticket page 200, IT_SUPPORT login 303 and support page 200. All servers stopped.','',
'## Five-case results','',
'| Variant | Retrieval code / fixture rank | Exact flag | Best score | Decision | Retrieval | Entity / check |','|---|---|---|---:|---|---|---|']
for row in summaries:
 entity='null / FAIL' if row['entity_error_code'] is None else CODE+' / PASS'
 notes.append(f"| `{row['variant']}` | {CODE} / 1 | true | {row['best_score']:.10f} | HIGH | PASS | {entity} |")
notes += ['', 'Every canonical string retains its original formatting. Both original/canonical-query extraction and normalized-query extraction yield 0x00000124. Normalization yields `windows blue screen error 0x00000124` and five BM25 tokens: windows, blue, screen, error, 0x00000124. The repeated error token in the prefix case is deduplicated; uppercase, quotes and exclamation marks do not change the normalized result.','',
'All complete ranked item dictionaries and solution objects compare exactly equal across all five, including IDs/order, contents, scores, flags and citations. Best-score differences are exactly zero in saved values. This is five controlled observations, not a population accuracy estimate.','',
'## Common ranking','',
'| Rank | Source | BM25 | Semantic | Raw hybrid | Bonus residual | Final score | Exact | Cited |','|---|---|---:|---:|---:|---:|---:|---|---|']
for idx,item in enumerate(r['items'],1):
 v=raw[item['source_id']]; bonus=v['hybrid_score']-.45*v['bm25_score']-.55*v['semantic_score']
 notes.append(f"| {idx} | {item['source_id']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {v['hybrid_score']:.6f} | {bonus:.2f} | {item['hybrid_score']:.6f} | {str(item['exact_error_match']).lower()} | {'Yes' if idx<=3 else 'No'} |")
notes += ['', 'Only the synthetic fixture is code-specific. Raw hybrid minus weighted BM25/semantic is 0.35000000000000003 for it and zero for the other returned sources in all five. This observes the positive exact-match branch, which IR-03 could not exercise; it is not a causal rank ablation.','',
'Fixture calculation: `(0.45*1 + 0.55*0.6980332879 + 0.35)*1.0 + 0.18 + 0.08 = 1.4439183083`. Approved-status trust is 1.0 and category/status metadata adds 0.26. Scores are ranking values, not calibrated probabilities.','',
'## Actual answer and applicability','', 'All five answers copy these same three source bodies:','', '~~~text',s['message'],'~~~','',
'The fixture caveat is visibly retained. The two cited historical records contain generic Windows driver/update resolutions and blank root causes. The input gives no OS version, update/restart trigger or confirmed driver fault; applicability of those repairs to this code remains unestablished. Rank-five software-installation evidence is unrelated to the stated fault and not used in the answer.','',
'Actual explanation:','',f"> {s['explanation']}",'','Actual suggested reply:','',f"> {s['suggested_reply']}",'',
'Actual HTML displays 144% retrieval confidence, whereas the explanation clamps to 100%; existing OBS-IR05-02 recurs. Validated-source wording and the follow-troubleshooting reply overstate applicability despite the preserved fixture caution; existing OBS-IR03-01 recurs. All five forms exhibit the same limitation, so it is not a formatting-induced transition or proof of a verified repair.','',
'All tickets: Windows / Updates, Medium priority, SOLUTION_PROPOSED/PENDING, absent from the support escalation queue. Text asking the reader to consult support is not actual application escalation or human acknowledgment. The third cited score is 0.5421971248, below UNCERTAIN 0.55; HIGH uses the best score and includes the first three. This is a recorded selection detail, not a separate threshold experiment. No real device repair occurred.','',
'Each run recorded two RuntimeError failures from llm.chat, zero successful returns and configured_enabled=false. Ten failed local attempts across five cases are not ten successful or rate-limited Groq requests. Only rule/evidence fallback was observed.','',
'## Auxiliary extraction defect and technical explanation','',
'**OBS-IR08-01:** uppercase 0X00000124 alone produced analysis.entities.error_code=null. The other four values are 0x00000124. This FAILS the separately predeclared entity consistency check.','',
'`ERROR_RE` requires lowercase 0x (`app/agents/ticket_agent.py:5`); `_entities()` searches original text (`:42-44`). In contrast, `normalize_query_for_search()` lowercases (`app/services/hybrid_search.py:97`), `_extract_error_codes()` lowercases (`:156`), and `tokenize()` lowercases matched alphanumeric tokens (`app/services/bm25.py:36`). `process_new_ticket()` passes canonical_issue rather than the entity field to `search_knowledge()` (`app/agents/coordinator.py:54`). The entity miss therefore did not affect this actual retrieval/answer path.','',
'## Impact, likelihood, severity and mitigation','',
'- Vulnerability identified: NO demonstrated security vulnerability; no formal VULN entry.',
'- Observed impact: uppercase diagnostic entity omitted, without ranking or answer change. No access/approval bypass, disclosure, executed repair or harm observed.',
'- Potential impact: consumers of the missing entity could lose structured context; those consumers were not tested. Unnecessary action from generic advice is plausible but no action was performed.',
'- Likelihood: one uppercase miss, explained by deterministic regex; prevalence and broader parser robustness unmeasured.',
'- Severity: Informational on the demonstrated security-impact scale; confirmed correctness defect, no assigned security vulnerability severity or exploit-risk score.',
'- Recommended mitigation: after approval, share case-insensitive code extraction/canonical entity output and add focused regression coverage. Separately verify action applicability and display ranking scores accurately. No fix applied.','',
'## Evidence, limits and conclusion','',
'Root inputs.json, fixture.json and expected_result.md preserve pre-execution definitions; source_preflight.json, preconditions.json and comparison_preflight.json preserve prerequisites. Each of five subdirectories holds input, stored-fixture preflight, token diagnostics, analysis, preprocessing, eligible corpus, both ranking stages, solution, ticket/citations, customer/support HTML, execution, terminal log and process result. comparison.json/comparison.csv and exact_boost_diagnostics.json contain derived comparisons; review.json is the later verdict.','',
'Saved HTML is an actual HTTP response, not a screenshot. Raw worker state intentionally remains awaiting review; review.json provides the assessment. All prior and raw current evidence remains unchanged. Source/data/evaluation/test and original main-database hashes remain unchanged. Main-file checksums do not cover unrelated concurrent WAL writes; the helper never writes the working database.','',
'The small synthetic corpus and fixture, five forms only, local environment and disabled Groq limit the result. No real diagnostic/repair accuracy, production deployment, other codes/boundaries, approval-workflow security or live LLM behavior is established. IR-03 remains Inconclusive. No IR-09 or later test executed.','',
'**Conclusion:** primary retrieval formatting PASS; auxiliary uppercase entity extraction FAIL. These scoped results do not establish recommendation safety or a security exploit. Stop before IR-09.','']
write(RUN/'notes.md','\n'.join(notes))
record=[
 '## IR-08 - Error-Code Formatting Variations','',
 '- Test ID: IR-08','- Test Name: Error-Code Formatting Variations',
 '- Test Objective: Compare code identity, exact-source retrieval and answer behavior across case/punctuation variants.',
 '- Component Being Tested: tokenize(), normalize_query_for_search(), _extract_error_codes(), hybrid_rank(), search_knowledge(), analyze_ticket()/_entities(), recommend_solution() and ticket workflow.',
 '- Input / Attack Scenario: Same title Windows blue screen report; sentence Windows blue screen error {variant}; variants 0x00000124, 0X00000124, error: 0x00000124, 0x00000124!!! and quoted "0x00000124". Exact 36/36/43/39/38-character inputs saved.',
 '- Preconditions: Original corpus lacks eligible code-specific evidence; predeclared plan permits one labelled isolated synthetic fixture. Same fixture plus original 427 eligible records in five fresh databases; backup, source hashes, users and configuration verified; Groq disabled.',
 '- Steps: Save inputs/fixture/criteria; seed each isolated corpus; normal login; submit each variant once; capture original preprocessing/ranking/answer, persisted state and HTTP pages; stop servers; compare all five.',
 '- Expected Behaviour: Code identity and exact-source relevance retained without a formatting-driven unsupported confident transition. Auxiliary entity extraction should also preserve equivalent codes; assess its result separately.',
 '- Actual Behaviour: All five normalize to windows blue screen error 0x00000124 and return identical source/score/flag arrays and solutions. Fixture first, exact=true, +0.35 raw bonus, HIGH 1.4439183083. Uppercase entities.error_code is null; other four populated. All SOLUTION_PROPOSED/PENDING.',
 f'- Evidence: [{REL}/notes.md]({REL}/notes.md), five-case comparison JSON/CSV, bonus diagnostics and complete original evidence in five subdirectories.',
 '- Observation: OBS-IR08-01 confirms case-sensitive auxiliary entity extraction. Generic repair applicability overstatement and score-as-percent display recur, equally across all forms; fixture caution is preserved.',
 '- Outcome: PASS (primary retrieval formatting on isolated fixture); FAIL (auxiliary uppercase entity check).',
 '- Vulnerability Identified: NO demonstrated security vulnerability; confirmed entity-field correctness defect.',
 '- Impact: Entity metadata missing for uppercase, without a retrieval/answer change in this path. No real repair, access bypass, data exposure or harm demonstrated. Generic recommendations remain unverified.',
 '- Likelihood: One observed uppercase miss explained by the regex; five planned examples do not estimate deployment prevalence.',
 '- Severity: Informational security observation; no formal vulnerability severity or exploit-risk score.',
 '- Technical Explanation: _entities uses case-sensitive ERROR_RE on original text. Retrieval gets canonical_issue and lowercases code extraction/normalization; the approved-status fixture gets exact bonus and trust/metadata adjustments. Equivalent normalized strings yield identical ranks.',
 '- Recommended Mitigation: After approval, use shared case-insensitive extraction/canonical entity values and regression coverage; separately verify action applicability and correct score labels. No application change applied.',
 '- Conclusion: Retrieval tolerance demonstrated only for the five forms and synthetic lookup control. Entity consistency fails; live Groq and actual code-specific repair remain untested. IR-03 stays Inconclusive. Stop before IR-09.',
]
for name,area in [('test_results.md','Formatting robustness'),('test_plan.md','Retrieval accuracy: code formatting')]:
 path=AUDIT/name; text=path.read_text(encoding='utf-8')
 text=text.replace('IR-08 through IR-15 remain Not run.','IR-08 passed primary retrieval formatting with an isolated fixture; its uppercase entity check failed. IR-09 through IR-15 remain Not run.',1)
 text,count=re.subn(r'^\| IR-08 \|.*$',f'| IR-08 | {area} | Completed (isolated fixture/fallback) | [{REL}/notes.md]({REL}/notes.md) | PASS (retrieval); FAIL (entity check) | NO security vulnerability demonstrated; entity defect |',text,flags=re.M); assert count==1
 if name=='test_results.md':
  text,count=re.subn(r'^## IR-08[^\n]*\n.*?(?=^## IR-09)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
 write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02, IR-04, IR-05, IR-06 and IR-07 cases','the completed IR-01, IR-02, IR-04, IR-05, IR-06, IR-07 and IR-08 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-07/: actual retrieval, escalation, manipulation, ambiguity and noisy-query evidence; IR-08 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-08/: actual case evidence, including the isolated formatting fixture; IR-09 through IR-15 remain reserved.')
text=text.replace('IR-08 through IR-15 remain Not run.',f'IR-08 passed retrieval formatting with a labelled isolated fixture; uppercase entity extraction failed separately. See [{REL}/notes.md]({REL}/notes.md). No code-specific repair is validated and IR-03 remains unchanged. IR-09 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence/README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-08/ through IR-15/ contain placeholders only.',f'IR-08/{RUN.name}/ contains five formatting variants using a labelled isolated fixture: primary retrieval PASS and auxiliary uppercase entity FAIL. IR-03 evidence remains unchanged. IR-09/ through IR-15/ contain placeholders only.')
write(path,text)
additions={
 'vulnerability_register.md':f'''## IR-08 review

IR-08 passes primary retrieval formatting for five planned forms using a labelled isolated fixture. Its separate uppercase entity check FAILS. No formal VULN entry is created. See [{REL}/notes.md]({REL}/notes.md).

- Observation ID: OBS-IR08-01.
- Title: Uppercase hexadecimal prefix omitted from ticket entity extraction.
- Related test / affected component: IR-08; ticket_agent.ERROR_RE and _entities().
- Description: 0X00000124 produces entities.error_code=null while the other four forms produce 0x00000124. Retrieval identity, exact fixture match and answers remain identical.
- Evidence: uppercase/analysis.json versus the other four analysis captures; comparison.json and identical retrieval/solution objects.
- Impact: structured error metadata absent for uppercase; no downstream retrieval, access-control or harmful-action effect observed. Other entity consumers were not tested.
- Likelihood: observed in one uppercase input; regex explains it deterministically. Deployment frequency and broader parser coverage are unmeasured.
- Severity: Informational on the demonstrated security-impact scale; confirmed correctness defect, no security vulnerability severity assigned.
- Risk level: no formal exploit-risk score; security consequence unproven.
- Technical explanation: analysis regex requires lowercase 0x on original text; retrieval lowercases extraction and receives canonical_issue rather than entities.error_code.
- Recommended mitigation: after approval, share case-insensitive extraction and normalize entity output; verify these forms with focused regression coverage.
- Status: documented; no fix applied.

Existing OBS-IR03-01 applicability overstatement and OBS-IR05-02 score display recur: the answer retains the fixture caution but also copies generic Windows repair histories and calls the sources validated; UI shows 144%, explanation 100%. All forms behave identically, so these are not formatting-induced changes or proof of a new exploit. The fixture does not validate a real diagnosis, repair or approval workflow. IR-03 remains Inconclusive.
''',
 'risk_matrix.md':f'''## IR-08 assessment

Primary formatting retrieval passed; the auxiliary entity check failed for uppercase 0X. OBS-IR08-01 is a correctness defect without a demonstrated security consequence in this route, since retrieval and answers are unchanged. No formal vulnerability risk score is assigned. Fixture limitations and recurring applicability/display concerns are recorded in [{REL}/notes.md]({REL}/notes.md).
''',
 'viva_notes.md':'''## IR-08 observed result

All five code-format variants passed primary retrieval comparison: same normalized query, exact fixture first, true exact-match flag, observed +0.35 bonus, HIGH 1.4439183083 and identical full answer. Because the original corpus has no eligible exact-code source, I used the predeclared option of a labelled synthetic article only in temporary databases. Its approved status is test metadata, not proof of a valid repair. IR-03 remains unchanged and Inconclusive.

A separate check failed: uppercase 0X00000124 was missing from analysis.entities.error_code. The entity regex requires lowercase 0x, while retrieval lowercases the canonical query and does not use the entity field. That explains why retrieval passes while structured extraction fails. No application fix or demonstrated exploit occurred.

The fallback copied the fixture's caution plus generic Windows repair history, while the explanation overstated validation and the page displayed 144% confidence. These limitations exist equally for all forms, so formatting parity is not proof of recommendation safety or real diagnostic accuracy. Groq was disabled and no repair was performed.
''',
 'commands.md':f'''## IR-08 reproduction after explicit case authorization

~~~powershell
.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir08.py
~~~

Executes five predeclared code-format variants once each, on five fresh temporary databases containing the same original synthetic corpus plus one labelled exact-code lookup fixture. Checks the existing private backup and preserves the working database, CSVs and application source. Saves original rankings, flags, answers, entities and HTTP pages; stops its servers. A rerun creates new evidence and is not needed to read the completed [{REL}/notes.md]({REL}/notes.md). IR-09 and later cases are not executed.
''',
}
for name,addition in additions.items():
 path=AUDIT/name; text=path.read_text(encoding='utf-8')
 if addition.splitlines()[0] not in text: write(path,text.rstrip()+'\n\n'+addition)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
current=hashes(RUN); assert all(current[name]==value for name,value in raw_before.items())
print('IR-08 retrieval PASS / auxiliary entity FAIL recorded. Prior and raw evidence unchanged. IR-09 through IR-15 unexecuted.')
