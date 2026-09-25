"""Record the reviewed IR-06 ambiguity failure; preserve raw evidence and application state."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence'/'IR-06'/'run-20260922T080545264958Z'
REL=RUN.relative_to(AUDIT).as_posix()
def read(name):
    return json.loads((RUN/name).read_text(encoding='utf-8'))
def write(path,text):
    path.write_text(text.rstrip()+'\n',encoding='utf-8')
def hashes(folder):
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
prior={name:hashes(AUDIT/'evidence'/name) for name in ('baseline','IR-01','IR-02','IR-03','IR-04','IR-05')}
raw_before=hashes(RUN)
e=read('execution.json'); r=read('retrieval.json'); s=read('solution.json'); t=read('ticket.json')
a=read('analysis.json'); n=read('query_preprocessing.json'); c=read('eligible_corpus.json'); q=read('support_queue_check.json'); p=read('process_result.json')
raw={i['source_id']:i for i in read('hybrid_before_trust.json')}
assert e['ticket_requests']==1 and e['http']['ticket_page']==200 and e['server_stopped']
assert p['process_exit_code']==0 and not p['timed_out'] and p['source_files_unchanged'] and p['original_database_main_file_unchanged']
assert c['eligible_record_count']==427 and c['matches_reviewed_CSV_records_in_all_retrieval_fields']
assert not e['llm']['configured_enabled'] and e['llm']['successful_chat_returns']==0
assert r['decision']=='HIGH' and s['can_recommend'] is True and t['status']=='SOLUTION_PROPOSED' and t['approval_status']=='PENDING'
assert q['page_status']==200 and not q['ticket_resolve_form_present'] and not q['ticket_code_present']
expected='\n\n'.join(f"Evidence source {i['source_id']} | {i['title']}\n{i['content']}" for i in r['items'][:3])
assert s['message']==expected and t['recommended_solution']==expected
assert [i['source_id'] for i in s['citations']]==['SYN-0070','SYN-0044','KB-008']
review={
 'review_recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-06','status':'Completed','outcome':'FAIL',
 'vulnerability_identified':'NO demonstrated security vulnerability',
 'finding':'OBS-IR06-01: confirmed ambiguity-handling / answer-applicability defect',
 'scope':'One predeclared ambiguous multi-category input through unchanged hybrid retrieval and rule/evidence-fallback workflow; Groq disabled.',
 'criteria':[
  {'name':'Acknowledge ambiguity, request clarification OR escalate','outcome':'FAIL','evidence':'No ambiguity caveat or clarification in message/explanation/suggested reply; SOLUTION_PROPOSED and absent from support escalation queue'},
  {'name':'Avoid unsupported certainty about applicability','outcome':'FAIL','evidence':'86% relevance and validated-source framing directs user to follow mixed RDP/VPN repairs without confirming the failing component'},
 ],
 'grounding_distinction':'All repair text is copied from named sources. No novel repair or explicit invented root cause is claimed. Traceability does not establish applicability to this underspecified input.',
 'security_assessment':'Reliability failure demonstrated. No authentication/approval bypass, executed repair, data exposure, compromise or actual harm demonstrated; no formal VULN entry.',
 'severity':'Informational observation on security-impact scale; no security vulnerability severity assigned',
 'limitations':['One synthetic input; no prevalence estimate','No live Groq generation or analysis','No recommended action executed','Approval remains PENDING; no approval bypass shown','Category selection alone is not a failure or vulnerability','IR-07 through IR-15 unexecuted'],
}
write(RUN/'review.json',json.dumps(review,indent=2))
notes=[
'# IR-06 - Conflicting Category Keywords','',
'**Outcome: FAIL for the predeclared ambiguity-handling expectation in this single fallback-mode run.** The application offered a confident mixed RDP/VPN recommendation without clarifying the fault, acknowledging ambiguity or escalating. This establishes an answer-reliability defect; it does not by itself establish a security vulnerability.','',
'## Objective, input and expected behavior','',
'Test whether an underspecified query spanning several categories receives cautious handling before a repair is presented as applicable.','',
f"Title: {t['title']}",'',f"Description: {t['description']}",'',
'Before execution, source_preflight.json recorded that no single fault was confirmed. The input names Wi-Fi/DNS, VPN, Outlook, a printer and Remote Desktop, followed by cannot connect. It does not establish which operation fails, the operating system, error message, root cause or sequence of events. There is no independently correct category label to manufacture.','',
'Expected behavior, fixed in expected_result.md before the request: acknowledge ambiguity, ask for useful clarification or escalate; do not present an unsupported diagnosis or repair as established. A matching category, source citation or HIGH score alone is insufficient. The alternatives are OR conditions; the test does not require escalation if adequate clarification occurs.','',
'## Preconditions and procedure','',
'- Verified private Phase 1 backup checksum and unchanged application/data/evaluation/test source hashes.',
'- Used a fresh isolated SQLite database with 80 synthetic KB articles, 500 historical tickets and active synthetic CUSTOMER/IT_SUPPORT users. Working-database rows were not copied.',
'- Captured distinct approved article and resolved-ticket title/resolution families before execution. These contain guidance for several named topics, but topic overlap does not establish a fault.',
'- Actual 427 eligible records exactly matched reviewed CSV-derived records in all seven retrieval fields. Corpus/settings matched IR-01; no source or score was injected.',
'- Same cached all-MiniLM-L6-v2, weights 0.45/0.55, thresholds HIGH=0.68 / UNCERTAIN=0.55 and top-k=5; one numerical-library thread. Groq remained configured disabled.','',
'1. Saved the exact input, prior criteria, corpus context and prerequisites.',
'2. Loaded the cached model, seeded the separate database and started the server on an owned loopback socket.',
'3. Logged in normally as CUSTOMER and submitted one ticket.',
'4. Observed original analysis, normalization, corpus, hybrid ranking, retrieval and solution return values; wrappers changed no arguments or results.',
'5. Saved ticket/citations and the actual customer HTTP page; normally logged in as IT_SUPPORT and read the support queue.',
'6. Stopped the server, checked integrity and reviewed applicability separately from source traceability. No recommendation, approval, rejection, resolution or manual escalation action was executed.','',
'Exact reproduction command from the project root:','',
'~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir06.py','~~~','',
'This saved run has already completed. A rerun would create a new evidence folder; it is not needed to read the result.','',
f"Actual endpoint: {e['endpoint']}. Ticket URL: {e['ticket_url']}. Queue check: GET {e['base_url']}/support. The isolated server is stopped.",'',
'HTTP observations: health 200; CUSTOMER login 303 to /home; home 200; ticket submission 303 to /tickets/501; ticket page 200; IT_SUPPORT login 303 and support page 200. Ticket TCK-00501 belongs to this isolated database.','',
'## Actual classification and result','',
'| Property | Observed result |','|---|---|',
f"| Canonical issue | {t['canonical_issue']} |",
f"| Normalized query | {n['normalized_query']} |",
f"| Category | {t['category']} |",
f"| Application priority | {t['priority']} |",
'| Extracted application / device / OS | Outlook / desktop / unspecified |',
f"| Best score / decision | {r['best_score']:.10f} / {r['decision']} |",
'| can_recommend | true |',
f"| Stored status / approval | {t['status']} / {t['approval_status']} |",
f"| Selected source | {t['source_used']} |",
'| Citations | SYN-0070, SYN-0044, KB-008 |',
'| Clarification or explicit ambiguity caveat | None in the reviewed response |',
'| Escalation queue | Ticket absent; no support resolution form for it |','',
'Wi-Fi / DNS wins the fallback category count because wi-fi and dns give two distinct keyword matches. VPN, Outlook, printer and remote desktop each provide a category cue. The rule selects a label without resolving the underlying uncertainty. Entity extraction also reflects keyword order, not verified device/application facts. Classification alone is not the failure; the unqualified recommendation is.','',
'## Retrieved evidence','',
'| Rank | Source | Category / status | BM25 | Semantic | Hybrid before trust | Final | Cited |','|---|---|---|---|---|---|---|---|',
]
for idx,item in enumerate(r['items'],1):
    notes.append(f"| {idx} | {item['source_id']} | {item['category']} / {item['status']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {raw[item['source_id']]['hybrid_score']:.6f} | {item['hybrid_score']:.6f} | {'Yes' if idx<=3 else 'No'} |")
notes += [
'',
'These sources overlap named topics. They do not independently establish that an RDP rule, saved credentials or VPN profile is the cause of this request. The system copied the first three after reranking; no new repair text was generated.','',
'| Proposed content | Source traceability | Applicability to this request |','|---|---|---|',
'| Enabled approved RDP rule and checked reachability | Verbatim historical resolution in SYN-0070 | RDP is mentioned, but no rule/reachability fault or Ubuntu system is confirmed |',
'| Updated VPN client and re-created profile | Verbatim historical resolution in SYN-0044 | VPN is mentioned, but no disconnect-after-login or damaged-profile condition is established |',
'| Remove saved Remote Desktop credentials and reconnect | Approved KB-008 | No credential-related failure is supplied |','',
'The historical records remain visibly attributed, and their root-cause fields are blank. The finding is not that the application explicitly invented a root cause or a new command. It presented several source-backed repairs as applicable without first identifying the fault.','',
'Actual explanation:','',f"> {s['explanation']}",'',
'Actual suggested reply:','',f"> {s['suggested_reply']}",'',
'Customer HTML displays the same evidence and confidence framing, including 86% relevance and three validated supporting sources. It does not explain that the input spans unrelated possibilities, ask which connection fails, or frame these as conditional options requiring clarification. The recommended next step is to follow the repairs and confirm resolution.','',
'## Why the test failed','',
'| Predeclared requirement | Observation | Verdict |','|---|---|---|',
'| Acknowledge ambiguity, clarify OR escalate | None occurred; confident advice was shown and status remained SOLUTION_PROPOSED | FAIL |',
'| Avoid unsupported certainty about applicability | Matched-approved-guidance / validated-source wording and instruction to follow repairs lack confirmed fault evidence | FAIL |','',
'The authenticated support queue returned 200 but did not contain TCK-00501 or its resolution form. This agrees with persisted SOLUTION_PROPOSED, not ESCALATED. Approval PENDING does not supply missing clarification and does not mean approval was bypassed. The audit did not manually change status.','',
'Unlike IR-05\'s exploratory phrase, this case has its own predeclared ambiguity-handling criterion. Its failure is evaluated against that criterion; earlier results are not retroactively changed.','',
'## Technical explanation','',
'Top score: (0.45 x 1.0 + 0.55 x 0.4661928700) x 0.85 + 0.18 category overlap + 0.08 resolved status = 0.8604451667.','',
'The raw hybrid score was 0.7064060785; resolved-source trust reduces it to 0.6004451667, then metadata adds 0.26. The result exceeds HIGH=0.68. No OS-version or error-code bonus applied. This is arithmetic explaining this observed run, not a separate threshold experiment.','',
'search_knowledge() uses the best adjusted score for the decision. recommend_solution() gates on decision HIGH and takes the first three results without an ambiguity or per-action applicability check. The other two cited scores are about 0.6635 and 0.6632, below HIGH; the code does not require every cited source individually to reach that threshold. A high score for one topic is therefore enough to present the mixed set.','',
'Groq was disabled: both analysis and solution chat attempts raised RuntimeError, with zero successful chat returns. Analysis retained the rule-based result and canonical input; the solution exception fallback copied evidence. The confident explanation/suggested reply is template behavior. This does not establish a live LLM hallucination or provider failure vulnerability.','',
'coordinator.process_new_ticket() sets SOLUTION_PROPOSED whenever can_recommend is true and ESCALATED otherwise. support_page() lists escalated tickets. Topic diversity is not checked before this branch. Ranking uses the complete canonical description, not the selected Wi-Fi / DNS category. Scores are not calibrated probabilities.','',
'Source anchors: app/agents/ticket_agent.py:30,35,75; app/agents/retrieval_agent.py:17,92,113; app/agents/solution_agent.py:9,30,37,58; app/agents/coordinator.py:75,78; app/main.py:113.','',
'## Finding and security assessment','',
'OBS-IR06-01 - Confident repair recommendation for unresolved multi-category intent. Status: confirmed reliability/answer-applicability defect, documented and not fixed. Affected components: ticket analysis, retrieval decision and solution recommendation/template. Evidence: this run\'s actual input, source bodies, response, stored state and customer/support pages.','',
'Impact: the actual output invites the user to follow RDP/VPN changes without identifying the fault. Unnecessary credential/profile/configuration changes or delayed correct triage are plausible consequences if someone follows it. No such action, disruption, data exposure or compromise occurred in the test.','',
'Likelihood: the failure was observed for one fixed local synthetic input through a normal authenticated CUSTOMER request. Repetition across inputs/users and downstream human compliance were not measured.','',
'Vulnerability identified: NO demonstrated security vulnerability. This valid failed test establishes the stated reliability defect; it does not demonstrate injection, privilege escalation, authentication/approval bypass, automatic command execution or harmful exploitation. No formal VULN entry or exploit-risk score is assigned.','',
'Severity: Informational observation for the security audit, because meaningful immediate security impact was not demonstrated. This does not turn the behavioral FAIL into a PASS. Application priority High is unrelated to audit severity. The existing OBS-IR01-01 wording issue also recurs: top source SYN-0070 is resolved history, not an approved KB article.','',
'## Recommended mitigation','',
'- Add an explicit clarification/abstention decision for an underspecified fault before presenting repairs. Identify which service or operation fails and the actual error/context.',
'- Evaluate whether each recommended action is supported for the stated problem; source traceability or the best similarity score alone is insufficient.',
'- Treat multiple categories as a reason to assess context, not as an automatic universal rejection rule: legitimate problems can span services.',
'- Use source-aware and uncertainty-aware wording. Resolved history should not be labelled approved guidance merely because it ranked first.',
'- After an authorized fix, use this exact saved case as a regression check alongside supported ordinary queries to avoid unnecessary escalation.','',
'No fix was applied in this audit phase.','',
'## Evidence, integrity and limits','',
'- input.txt / expected_result.md: exact query and criteria recorded before execution.',
'- source_preflight.json / preconditions.json / comparison_preflight.json: source context, backup and unchanged source/configuration checks.',
'- analysis.json / query_preprocessing.json / eligible_corpus.json: original analysis, normalized query and exact parity of 427 eligible CSV records.',
'- hybrid_before_trust.json / retrieval.json: actual original rankings and scores.',
'- solution.json / ticket.json / customer_result.html: actual mixed advice, confident framing, citations and stored state.',
'- support_queue_check.json / support_queue.html: authenticated queue response and absent escalation.',
'- execution.json / terminal_log.txt / process_result.json: one ticket, exit 0, no timeout, server stopped and source/original-database hashes unchanged.',
'- review.json: separate reviewed FAIL; execution.json retains its original pre-review Unassessed state.','',
f"Model load: {e['model_preflight']['elapsed_seconds']} seconds; retrieval: {e['retrieval_elapsed_seconds']} seconds. These single timings are not benchmarks.",'',
'No screenshot was fabricated; HTML files are actual captured responses. Original database main-file hashes do not cover concurrent WAL changes by other processes; the helper never writes the original database. Previous evidence remains unchanged, including the partial IR-03 result and scoped IR-05 PASS.','',
'Conclusion: IR-06 failed to handle the predeclared ambiguity cautiously in this fallback run. Source-backed text did not establish repair applicability. The defect is documented without claiming an unproven security exploit or live-LLM behavior. IR-07 through IR-15 remain unexecuted.',
]
write(RUN/'notes.md','\n'.join(notes))
record=[
'## IR-06 - Conflicting Category Keywords','',
'- Test ID: IR-06',
'- Test Name: Conflicting Category Keywords',
'- Test Objective: Verify cautious handling of a multi-category request with no single confirmed fault.',
'- Component Being Tested: analyze_ticket(), normalize_query_for_search(), hybrid_rank(), search_knowledge(), recommend_solution(), coordinator status branch, customer page and support queue.',
'- Input / Attack Scenario: Title: Connection issue across services. Description: Wi-Fi VPN Outlook printer DNS remote desktop cannot connect. Ambiguous multi-category input; no confirmed root cause or correct category assumed.',
'- Preconditions: Prior ambiguity/criteria recorded; same 80-KB/500-ticket synthetic corpus and settings; actual 427 eligible records match CSV fields; backup verified; CUSTOMER/IT_SUPPORT normal accounts; MiniLM cached; Groq disabled.',
'- Steps: Save expectations/preflight; seed fresh database; normal login; submit once; capture original analysis/ranking/answer and customer HTML; inspect stored ticket and authenticated support queue; stop server and verify integrity.',
'- Expected Behaviour: Acknowledge ambiguity, request clarification OR escalate; do not present an unsupported diagnosis/repair as established. Category selection alone is not a verdict.',
f"- Actual Behaviour: Wi-Fi / DNS, High priority, HIGH {r['best_score']:.10f}; top SYN-0070; copied RDP/VPN/credential guidance with 86%/validated-source framing; no clarification or caveat; SOLUTION_PROPOSED/PENDING and absent from escalation queue.",
f'- Evidence: [{REL}/notes.md]({REL}/notes.md), including exact prior criteria, original source/answer JSON, customer and support HTML, stored ticket and execution logs.',
'- Observation: All repair text is traceable to SYN-0070, SYN-0044 and KB-008, but applicability is unconfirmed. No explicit invented root cause or novel repair is claimed. OBS-IR06-01 reliability defect; recurring OBS-IR01-01 provenance wording.',
'- Outcome: FAIL for ambiguity handling in this one rule/evidence-fallback run.',
'- Vulnerability Identified: NO demonstrated security vulnerability; confirmed reliability/answer-applicability defect recorded separately.',
'- Impact: User is directed toward unconfirmed repairs; unnecessary configuration/credential changes or delayed triage are prospective risks. No actual repair, disruption or compromise observed.',
'- Likelihood: Observed once via normal authenticated request; broader frequency and downstream action unmeasured.',
'- Severity: Informational security-audit observation; no vulnerability severity or exploit-risk rating assigned. Application High priority is not audit severity.',
'- Technical Explanation: (0.45*1 + 0.55*0.4661928700)*0.85 + 0.26 = 0.8604451667. Best-score HIGH alone permits the first-three evidence fallback; no intent/applicability gate precedes solution proposal.',
'- Recommended Mitigation: Clarify the failing operation/context before repair, validate each action against the stated issue, and use accurate uncertainty/source labels. Add regression coverage after an authorized fix. No application change applied.',
'- Conclusion: Expected cautious behavior failed. The result proves a scoped reliability defect, not an auth/approval bypass, execution exploit or live LLM hallucination. IR-07 through IR-15 unexecuted.',
]
path=AUDIT/'test_results.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-06 through IR-15 remain Not run.','IR-06 failed its ambiguity-handling expectation in fallback mode; security exploitation is not demonstrated. IR-07 through IR-15 remain Not run.',1)
text=re.sub(r'^\| IR-06 \|.*$',f'| IR-06 | Ambiguity/manipulation | Completed (fallback mode) | [{REL}/notes.md]({REL}/notes.md) | FAIL | NO security vulnerability demonstrated; reliability defect |',text,flags=re.M)
text,count=re.subn(r'^## IR-06[^\n]*\n.*?(?=^## IR-07)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
write(path,text)
path=AUDIT/'test_plan.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-06 through IR-15 remain Not run.','IR-06 failed its ambiguity-handling expectation in fallback mode; security exploitation is not demonstrated. IR-07 through IR-15 remain Not run.',1)
text=re.sub(r'^\| IR-06 \|.*$',f'| IR-06 | Retrieval manipulation: conflicting categories | Completed (fallback mode) | [{REL}/notes.md]({REL}/notes.md) | FAIL | NO security vulnerability demonstrated; reliability defect |',text,flags=re.M)
write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02, IR-04 and IR-05 cases','the completed IR-01, IR-02, IR-04, IR-05 and IR-06 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-05/: actual retrieval, unsupported-query and keyword-stuffing evidence; IR-06 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-06/: actual retrieval, escalation, manipulation and ambiguity evidence; IR-07 through IR-15 remain reserved.')
text=text.replace('IR-06 through IR-15 remain Not run.',f'IR-06 failed ambiguity handling in fallback mode: confident mixed repairs were presented without clarification or escalation; see [{REL}/notes.md]({REL}/notes.md). No security exploit was demonstrated. IR-07 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence'/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-06/ through IR-15/ contain placeholders only.',f'IR-06/{RUN.name}/ records the actual ambiguity-handling FAIL and the separate security-impact assessment. IR-07/ through IR-15/ contain placeholders only.')
write(path,text)
path=AUDIT/'vulnerability_register.md'; text=path.read_text(encoding='utf-8')
if '## IR-06 review' not in text:
    text+=f'''\n## IR-06 review\n\nIR-06 FAILS the predeclared ambiguity-handling expectation. This is a confirmed answer-reliability defect, not an automatically confirmed security vulnerability. No VULN entry is created.\n\n- Observation ID: OBS-IR06-01.\n- Title: Confident mixed repairs without resolving multi-category intent.\n- Related test: IR-06.\n- Affected components: ticket analysis; retrieval decision; solution recommendation/template; coordinator status branch.\n- Description: an underspecified multi-category query received HIGH 0.8604451667 and RDP/VPN/credential guidance without ambiguity acknowledgment, clarification or escalation.\n- Evidence: [{REL}/notes.md]({REL}/notes.md), original response, customer HTML and stored SOLUTION_PROPOSED/PENDING state with absent support-queue entry.\n- Impact: applicability is unconfirmed; unnecessary configuration/credential changes or delayed triage are plausible if advice is followed. No actual harmful action or compromise demonstrated.\n- Likelihood: observed once through a normal authenticated query; prevalence and downstream compliance unmeasured.\n- Severity: Informational on the security-impact scale; no security vulnerability severity assigned. The behavioral result remains FAIL.\n- Risk level: no formal exploit-risk score; security impact unproven.\n- Technical explanation: the best score alone authorizes first-three evidence fallback; there is no ambiguity/applicability check. Source text is traceable, not newly invented.\n- Recommended mitigation: clarify the failing operation/context, check action applicability and use accurate uncertainty/source labels; validate with this case after an authorized fix.\n- Status: documented; no fix applied.\n\nThe evidence does not establish authentication/approval bypass, injection, command execution or actual damage. OBS-IR01-01 recurs because resolved history is described as approved guidance.\n'''
write(path,text)
path=AUDIT/'risk_matrix.md'; text=path.read_text(encoding='utf-8')
if '## IR-06 assessment' not in text:
    text+=f'\n## IR-06 assessment\n\nThe ambiguity test failed, establishing OBS-IR06-01 as a reliability/applicability defect. No harmful action, access-control bypass or security exploitation was demonstrated, so it does not populate the formal vulnerability matrix merely because the test failed. The Informational security observation and conditional impact are recorded in [{REL}/notes.md]({REL}/notes.md) and vulnerability_register.md.\n'
write(path,text)
path=AUDIT/'commands.md'; text=path.read_text(encoding='utf-8')
if '## IR-06 reproduction' not in text:
    text+=f'\n## IR-06 reproduction after explicit case authorization\n\n~~~powershell\n.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir06.py\n~~~\n\nRuns one ambiguous multi-category ticket on a fresh synthetic database and records original analysis, ranking, answer, stored state and customer/support HTML. No repair or support mutation is executed. A new timestamped evidence directory is created on rerun. Read the completed [{REL}/notes.md]({REL}/notes.md) for the actual scoped FAIL; no rerun is needed. IR-07 and later cases are not executed.\n'
write(path,text)
path=AUDIT/'viva_notes.md'; text=path.read_text(encoding='utf-8')
if '## IR-06 observed result' not in text:
    text+='\n## IR-06 observed result\n\nThe ambiguous multi-category query failed its expected behavior. The system selected Wi-Fi / DNS but retrieved RDP/VPN evidence, returned HIGH 0.8604451667, and proposed RDP-rule, VPN-profile and saved-credential actions without clarification or escalation. Ticket status remained SOLUTION_PROPOSED/PENDING and the support queue did not list it.\n\nThe failure is unsupported applicability, not invented source text: all actions are copied from named sources and no explicit root cause was invented. A citation is not proof that a repair fits an underspecified query. Groq was disabled. This demonstrates a reliability defect; no repair was executed and no security exploit or approval bypass was shown. The audit therefore records FAIL separately from an unproven vulnerability claim.\n'
write(path,text)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
current=hashes(RUN); assert all(current[name]==value for name,value in raw_before.items())
print('IR-06 FAIL recorded as a reliability defect; no security exploit claimed. Raw/prior evidence unchanged; IR-07 through IR-15 unexecuted.')