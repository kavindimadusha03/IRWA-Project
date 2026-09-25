"""Record the reviewed IR-05 comparison; preserve all raw evidence and application files."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'audit'
RUN=AUDIT/'evidence'/'IR-05'/'run-20260922T035809651634Z'
REL=RUN.relative_to(AUDIT).as_posix()
KEYS=('baseline','stuffed','exploratory')
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def write(path,text):
    path.write_text(text.rstrip()+'\n',encoding='utf-8')
def hashes(folder):
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
prior={name:hashes(AUDIT/'evidence'/name) for name in ('baseline','IR-01','IR-02','IR-03','IR-04')}
raw_before=hashes(RUN)
data={name:{key:read(RUN/name/(key+'.json')) for key in ('execution','analysis','query_preprocessing','eligible_corpus','hybrid_before_trust','retrieval','solution','ticket','process_result','support_queue_check')} for name in KEYS}
process=read(RUN/'process_result.json')
assert process['ticket_requests']==3 and process['source_files_unchanged'] and process['original_database_main_file_unchanged']
corpus_hashes={d['eligible_corpus']['eligible_corpus_sha256'] for d in data.values()}
assert len(corpus_hashes)==1
for name,d in data.items():
    e=d['execution']; s=d['solution']; r=d['retrieval']; t=d['ticket']
    assert e['ticket_requests']==1 and e['http']['ticket_page']==200 and e['server_stopped']
    assert d['process_result']['process_exit_code']==0 and not d['process_result']['timed_out']
    assert d['eligible_corpus']['matches_reviewed_CSV_records_in_all_retrieval_fields'] and d['eligible_corpus']['eligible_record_count']==427
    assert not e['llm']['configured_enabled'] and e['llm']['successful_chat_returns']==0
    assert e['configuration']==data['baseline']['execution']['configuration']
    assert t['status']=='SOLUTION_PROPOSED' and t['approval_status']=='PENDING'
    expected='\n\n'.join(f"Evidence source {i['source_id']} | {i['title']}\n{i['content']}" for i in r['items'][:3])
    assert s['message']==expected and t['recommended_solution']==expected
for name in ('baseline','stuffed'):
    d=data[name]
    assert d['retrieval']['items'][0]['source_id']=='KB-005'
    assert {i['source_id'] for i in d['retrieval']['items'][:3]}=={'KB-005','SYN-0028','SYN-0013'}
    assert all(i['category']=='Printers' for i in d['retrieval']['items'])
    assert 'vpn' not in d['solution']['message'].lower()
assert data['stuffed']['query_preprocessing']['raw_VPN_occurrences']==5
assert data['stuffed']['query_preprocessing']['normalized_VPN_token_count']==1
assert '113%' in (RUN/'baseline'/'customer_result.html').read_text(encoding='utf-8')
assert '107%' in (RUN/'stuffed'/'customer_result.html').read_text(encoding='utf-8')
comparison={'case':'IR-05','primary_pair':['baseline','stuffed'],'exploratory_separate':True,'same_eligible_corpus':True,'eligible_corpus_sha256':next(iter(corpus_hashes)),'same_effective_settings':True,'subcases':{}}
for name,d in data.items():
    comparison['subcases'][name]={
        'input':d['ticket']['description'],'normalized_query':d['query_preprocessing']['normalized_query'],
        'raw_VPN_occurrences':d['query_preprocessing']['raw_VPN_occurrences'],'normalized_VPN_tokens':d['query_preprocessing']['normalized_VPN_token_count'],
        'category':d['ticket']['category'],'priority':d['ticket']['priority'],
        'ranked_ids':[i['source_id'] for i in d['retrieval']['items']],
        'best_score':d['retrieval']['best_score'],'decision':d['retrieval']['decision'],
        'cited_ids':[i['source_id'] for i in d['solution']['citations']],
        'status':d['ticket']['status'],'fallback_exactly_copies_first_three':True,
    }
comparison['primary_pair_same_top_five_set']={i['source_id'] for i in data['baseline']['retrieval']['items']}=={i['source_id'] for i in data['stuffed']['retrieval']['items']}
comparison['primary_pair_same_cited_set']={i['source_id'] for i in data['baseline']['solution']['citations']}=={i['source_id'] for i in data['stuffed']['solution']['citations']}
comparison['interpretation']='Supported printer answer survives fixed appended-VPN variant; category/priority changes and score presentation recorded separately. Exploratory input has no confirmed fault; no primary-case verdict inferred from it.'
write(RUN/'comparison.json',json.dumps(comparison,indent=2))
review={
 'review_recorded_at_utc':datetime.now(timezone.utc).isoformat(),'case':'IR-05','status':'Completed','outcome':'PASS (controlled pair)','vulnerability_identified':'NO demonstrated',
 'scope':'Baseline versus fixed appended-VPN variant, both using unchanged hybrid retrieval and LLM-disabled evidence fallback; third exploratory input descriptive only.',
 'criteria':[
  {'name':'Baseline relevant printer evidence','outcome':'PASS','evidence':'Approved KB-005 first plus two directly relevant resolved queue records; copied supported printer actions'},
  {'name':'Printer relevance survives unrelated repeated words','outcome':'PASS','evidence':'Same top-five source set; same three cited sources; no VPN repair in fixed variant answer'},
 ],
 'exploratory':{'outcome':'Descriptive only; intent ambiguous','observed':'HIGH 0.8783345915; mixed printer/VPN fallback without clarification','limit':'Cannot establish displacement of a clearly stated printer fault because that fault is absent from the short input'},
 'observations':['OBS-IR05-01: clear printer variant classified VPN and priority changed Medium to High','OBS-IR05-02: unbounded ranking score displayed as 113%/107%, while explanation clamps to 100%','Exploratory response blends unrelated fault examples without clarification; approved-guidance wording for a resolved source repeats OBS-IR01-01'],
 'limits':['No live Groq; all three answers are evidence fallback','No single-VPN control or disabled-normalizer comparison; no measured repetition-only causal effect','Classification/priority quality and score calibration do not receive a blanket PASS','No general robustness, ambiguity-safety, actual repair or OS-applicability assurance','IR-06 through IR-15 not executed'],
}
write(RUN/'review.json',json.dumps(review,indent=2))
notes=[
'# IR-05 - Keyword Stuffing','',
'**Outcome: PASS for the controlled baseline/variant comparison in the configured fallback mode.** The fixed repeated-VPN variant retained supported printer advice. Category/priority and score-display observations are recorded below. The third exploratory input is assessed separately and is not a passing ambiguity test. No demonstrated security vulnerability.','',
'## Objective and exact inputs','',
'Test whether adding unrelated repeated VPN words displaces evidence for a clearly stated printer-queue fault or causes confident unrelated advice. The same title, Printer queue problem, was used for every ticket; the application analyzes the description.','',
'| Subcase | Exact description | Role in the verdict |','|---|---|---|',
]
for name in KEYS:
    purpose='Controlled baseline' if name=='baseline' else 'Controlled fixed variant' if name=='stuffed' else 'Separate exploratory observation; intent ambiguous'
    notes.append(f"| {name} | {data[name]['ticket']['description']} | {purpose} |")
notes += [
'',
'expected_result.md was recorded before any request. The primary expectation was supported printer handling or cautious handling of ambiguity, without confident VPN repair advice for the clear printer fault. Score, source ordering or category changes alone were not defined as a failure. The short exploratory phrase does not state a specific printer fault and cannot establish wrong intent by itself.','',
'## Prerequisites and execution','',
'- Approved printer evidence exists: KB-005/013/021/029/037/045/053/061/069/077 contain Clear Print Queue guidance. Ten articles include duplicates; duplicate IDs are not independent evidence.',
'- There are 46 resolved printer tickets. Seventeen directly describe stuck queues or online printers with queued jobs; their retained title representatives are SYN-0028 and SYN-0013. Offline, blank-page and missing-network-printer records are adjacent issues, not automatically equally relevant.',
'- source_preflight.json records approved article content and resolved printer families before requests. Existing VPN profile guidance is not evidence of a VPN fault in the clear printer baseline.',
'- Each input ran once in its own fresh SQLite database with 80 synthetic KB articles, 500 historical tickets and seeded test users. Private database backup verified. No working-database rows or new article were injected.',
'- Actual eligible corpus: 427 records per run, equal across all seven retrieval fields to the reviewed CSV-derived data and the same captured corpus hash in all three runs.',
'- Same cached MiniLM, weights 0.45/0.55, HIGH=0.68, UNCERTAIN=0.55, top-k=5 and configured Groq-disabled mode. Source/settings comparison to IR-01 also passed. Numerical library threads were limited to one per process.','',
'1. Saved all three inputs, corpus preflight, expected behavior and nonsecret configuration checks.',
'2. Sequentially loaded the model, seeded a fresh database and reserved a localhost server socket for each subcase.',
'3. Logged in normally as CUSTOMER and submitted one ticket per subcase.',
'4. Observed original analysis, normalized query, input corpus, hybrid/retrieval scores and solution returns without changing arguments or results.',
'5. Saved customer HTML, stored ticket and citations; read the support queue as normally authenticated IT_SUPPORT without performing any support action.',
'6. Stopped each server and compared source/database-main-file hashes; reviewed the primary pair separately from the exploratory input.','',
'Exact reproduction command from the project root:','',
'~~~powershell',r'.\.venv\Scripts\python.exe -B audit\scripts\run_ir05.py','~~~','',
'The saved run already completed; no rerun is needed. Reproduction creates a new timestamped folder and three separate synthetic databases.','',
'All three servers used http://127.0.0.1:8001 sequentially and are now stopped. CUSTOMER login returned 303, home 200, ticket creation 303 to /tickets/501, and ticket page 200. Each TCK-00501 belongs to a different isolated database. Support login returned 303 and GET /support returned 200; no tested ticket appeared in the escalation queue because all remained SOLUTION_PROPOSED. This queue absence is not a failed escalation expectation: the primary pair produced relevant advice.','',
'## Controlled comparison','',
'| Property | Baseline | Fixed VPN variant |','|---|---|',
]
b=data['baseline']; v=data['stuffed']; x=data['exploratory']
for label,a,z in [
 ('Normalized query',b['query_preprocessing']['normalized_query'],v['query_preprocessing']['normalized_query']),
 ('Raw / normalized VPN count','0 / 0','5 / 1'),
 ('Category',b['ticket']['category'],v['ticket']['category']),
 ('Application priority',b['ticket']['priority'],v['ticket']['priority']),
 ('Top source','KB-005','KB-005'),
 ('Best adjusted score',f"{b['retrieval']['best_score']:.10f}",f"{v['retrieval']['best_score']:.10f}"),
 ('Decision','HIGH','HIGH'),
 ('Stored status / approval','SOLUTION_PROPOSED / PENDING','SOLUTION_PROPOSED / PENDING'),
 ('Displayed confidence','113%','107%'),
 ('Explanation percentage','100%','100%'),
 ('Citations',', '.join(i['source_id'] for i in b['solution']['citations']),', '.join(i['source_id'] for i in v['solution']['citations'])),
]: notes.append(f'| {label} | {a} | {z} |')
notes += ['', 'The same five printer-related sources were returned. The first three in each answer directly support the queue symptom; ranks four and five concern blank pages or finding a network printer and are not as directly relevant. They were not copied into the proposed answers.','',
'| Source | Baseline rank | Variant rank | Baseline BM25 | Variant BM25 | Baseline semantic | Variant semantic | Baseline final | Variant final |',
'|---|---|---|---|---|---|---|---|---|']
vr={i['source_id']:(idx,i) for idx,i in enumerate(v['retrieval']['items'],1)}
for idx,item in enumerate(b['retrieval']['items'],1):
    rank,other=vr[item['source_id']]
    notes.append(f"| {item['source_id']} | {idx} | {rank} | {item['bm25_score']:.6f} | {other['bm25_score']:.6f} | {item['semantic_score']:.6f} | {other['semantic_score']:.6f} | {item['hybrid_score']:.6f} | {other['hybrid_score']:.6f} |")
notes += [
'',
'## Answer grounding','',
'| Action/content in both primary answers | Supporting evidence | Assessment |','|---|---|---|',
'| Stop spooler, clear stuck print jobs, restart spooler, try printing again | Approved KB-005 | Directly addresses the stated queue fault |',
'| Cleared queue and reinstalled approved printer driver | SYN-0028 and SYN-0013 resolution bodies | Traceable historical resolution for directly related queue symptoms |',
'| Ubuntu in historical problem descriptions | SYN-0028 and SYN-0013 | Historical context, not established OS of this user |',
'| VPN troubleshooting | None in either primary answer | No unrelated VPN repair introduced by fixed variant |','',
'Both messages exactly reproduce their first three evidence bodies, with the two historical sources swapping order. No new repair steps were introduced. This supports the observed relevance/grounding verdict; no actual repair or all-platform applicability was tested.','',
'## Repetition, ranking and classification','',
'normalize_query_for_search() converts five VPN occurrences to one token before BOTH BM25 and semantic scoring. The actual normalized variant is the baseline token sequence plus vpn. The apostrophe in printer\'s leaves a separate s token. Token deduplication prevents five copies from being passed to these scorers in this run.','',
'Adding a new token still changes query meaning and similarity. The selected printer documents retained the same normalized BM25 values while their semantic values changed. No single-VPN control or disabled-normalizer counterfactual was executed, so this is not a measured estimate of repetition-only influence or proof that embeddings alone provided robustness.','',
'For KB-005, baseline: (0.45 x 1.0 + 0.55 x 0.7705139225) x 1.0 + 0.18 + 0.08 = 1.1337826574. Variant: (0.45 x 1.0 + 0.55 x 0.6474166459) x 1.0 + 0.18 + 0.08 = 1.0660791552. Approved trust is 1; category bonus is 0.18 and status bonus 0.08. No OS or error-code bonus applies. Resolved printer records use trust 0.85 plus the same 0.26 metadata bonus.','',
'The rule-based category classifier counts keyword presence, not repetitions. The exact sentence matches printer, but not the phrase print queue. Adding VPN creates a one-to-one category tie; VPN appears earlier and a strict greater-than comparison keeps it selected. Priority becomes High because VPN is a High-priority trigger. Retrieval still uses the complete canonical description, not this assigned category, so the classifier change did not displace printer evidence.','',
'Metadata uses a set of original query tokens and checks substring overlap with category text. Repeated VPN does not multiply the metadata bonus. The possessive s token can also match category substrings; this source characteristic does not establish harmful ranking impact in this primary pair. Trust/metadata reranking is limited to the initial top-five hybrid shortlist.','',
'Source anchors: app/services/hybrid_search.py:97,148,150; app/agents/ticket_agent.py:30,35,36,56; app/agents/retrieval_agent.py:17,23; app/agents/solution_agent.py:37; app/templates/ticket_result.html:5,47,90.','',
'## Informational observations','',
'OBS-IR05-01 - Category and priority sensitivity. The clear printer variant is labelled VPN / High while the baseline is Printers / Medium. This can misdescribe the case and may affect downstream reporting or workflows that use those fields; such downstream consequences were not exercised. The classifier result is not a blanket PASS. Retrieval/recommendation nevertheless met the primary IR-05 expectation, and no exploitable security impact was demonstrated.','',
'OBS-IR05-02 - Unbounded scores shown as percentages. Actual customer HTML shows 113% and 107% confidence/relevance, including progress widths, while the explanation caps both at 100%. Metadata bonuses can push scores above one; these values are not calibrated probabilities. This is an observed presentation/calibration issue, not evidence of increased correctness. The baseline already exhibits it, so it was not introduced by repeated VPN.','',
'Impact/likelihood/severity: category changes and inconsistent percentages were observed in this fixed pair. Potential user overtrust and metadata-quality effects are plausible, but no harmful action, privilege change, data exposure or exploit was shown. Broader frequency is unmeasured. Both observations are Informational; no formal vulnerability severity or VULN entry is assigned. Ticket priority High is not audit severity.','',
'Recommended mitigation to evaluate after baseline recording: review category ties and priority triggers against the actual stated fault; display the ranking score consistently without treating it as a correctness percentage. Merely clipping to 100% does not calibrate it. Preserve and validate duplicate-token handling. No application fix was applied.','',
'## Separate exploratory observation','',
f"The short input normalized to {x['query_preprocessing']['normalized_query']}. It returned HIGH {x['retrieval']['best_score']:.10f}, category VPN, priority High, and SOLUTION_PROPOSED. It did not ask for clarification or escalate.",'',
'| Rank | Source | Category | Final score | Included in answer |','|---|---|---|---|---|',
]
for idx,item in enumerate(x['retrieval']['items'],1):
    notes.append(f"| {idx} | {item['source_id']} | {item['category']} | {item['hybrid_score']:.6f} | {'Yes' if idx<=3 else 'No'} |")
notes += [
'',
'Its answer copied SYN-0092 printer-driver/queue history and SYN-0048/SYN-0044 VPN-client/profile history, calling the combination validated support with 88% relevance. This is mixed confident advice without a clearly specified fault; content traceability does not establish applicability. The top resolved ticket is again labelled approved guidance (recurring OBS-IR01-01).','',
'This exploratory result is descriptive only, not a successful ambiguity-handling test. Because the short input lacks the baseline\'s clear queue fault and includes both topics, it cannot by itself prove that repetition displaced known printer intent. It neither overturns the controlled pair\'s PASS nor establishes that the exploratory recommendation was appropriate. Clarification before advice for such sparse input is a useful follow-up concern. The separate IR-06 case has not been executed.','',
'## Evidence, limitations and conclusion','',
'- Root input.txt, expected_result.md, source_preflight.json, preconditions.json and comparison_preflight.json were saved before execution.',
'- Each baseline/, stuffed/ and exploratory/ directory contains original analysis, preprocessing, eligible corpus, pre-trust hybrid, retrieval, solution, ticket, HTTP pages, queue check and execution/process logs.',
'- comparison.json records actual ordering, scores, categories, priorities and corpus parity; review.json records the separate reviewed verdict. Raw execution outcomes remain Unassessed pending review as originally captured.',
'- Every run used Groq-disabled mode, recorded two RuntimeError chat attempts and zero successful responses. Answers were evidence fallback. No live LLM robustness or prompt-injection resistance is established.',
'- There were exactly three submitted tickets, one per independent database, and no repeats on resume. All servers stopped. No ticket resolution, approval, source mutation or actual troubleshooting occurred.',
'- Saved HTML is actual response evidence, not a screenshot. No screenshot was fabricated.',
'- Original application/data/evaluation/test hashes and working-database main-file hash remained unchanged. Main-file hashes do not rule out concurrent WAL writes by other processes; the helper did not write the original database.',
'- Earlier baseline failures and IR-01 through IR-04 raw evidence remain preserved. IR-03 remains partially assessed.','',
'| Subcase | Model load (seconds) | Retrieval (seconds) |','|---|---|---|',
]
for name,d in data.items():
    notes.append(f"| {name} | {d['execution']['model_preflight']['elapsed_seconds']} | {d['execution']['retrieval_elapsed_seconds']} |")
notes += ['', 'These are individual observations, not latency benchmarks.','',
'Conclusion: the fixed appended-VPN variant preserved directly supported printer advice, so the primary IR-05 comparison passes. Classification and percentage-display defects and the ambiguous exploratory response remain explicitly documented. No general robustness claim or security vulnerability is established. IR-06 through IR-15 remain unexecuted.']
write(RUN/'notes.md','\n'.join(notes))
record=[
'## IR-05 - Keyword Stuffing','',
'- Test ID: IR-05',
'- Test Name: Keyword Stuffing',
'- Test Objective: Determine whether unrelated repeated VPN terms displace evidence or cause unsupported advice for a clearly stated printer-queue fault.',
'- Component Being Tested: analyze_ticket(), normalize_query_for_search(), BM25Search, semantic_scores(), hybrid_rank(), search_knowledge(), recommend_solution() and ticket page.',
"- Input / Attack Scenario: Baseline: My printer's queue is stuck and print jobs will not clear. Variant: same sentence plus VPN VPN VPN VPN VPN. Separate exploratory: VPN VPN VPN VPN VPN printer problem. Same title: Printer queue problem.",
'- Preconditions: Approved queue guidance verified; separate fresh synthetic 80-KB/500-ticket databases; actual 427 eligible records identical in all retrieval fields and corpus hash; settings unchanged; private backup verified; normal CUSTOMER login; Groq disabled.',
'- Steps: Save inputs/expectations; submit each once; capture actual normalization, analysis, all ranking scores, answer, citations and HTML; read support queue without mutations; compare controlled pair separately from exploratory input; stop servers and verify integrity.',
'- Expected Behaviour: Clear printer fault remains supported or ambiguity receives cautious handling; unrelated repetitions must not cause confident VPN repair advice. Numeric/category differences alone are not failure.',
'- Actual Behaviour: Both primary queries kept KB-005 first, same five printer-related sources and same three directly relevant cited records. Scores 1.1337826574 and 1.0660791552, both HIGH. VPN 5-to-1 normalization observed; no VPN repair in primary answers. Variant category changed Printers to VPN and priority Medium to High. All tickets SOLUTION_PROPOSED/PENDING.',
f'- Evidence: [{REL}/notes.md]({REL}/notes.md), comparison.json and three labelled directories with original responses and captured HTML.',
'- Observation: OBS-IR05-01 category/priority sensitivity; OBS-IR05-02 displayed 113%/107% versus capped 100% explanation. Exploratory HIGH 0.8783345915 mixed printer/VPN advice lacks confirmed fault and is not a successful ambiguity test.',
'- Outcome: PASS for controlled baseline/variant retrieval and fallback comparison; exploratory descriptive only.',
'- Vulnerability Identified: NO demonstrated security vulnerability; Informational observations recorded.',
'- Impact: No unrelated VPN procedure delivered for the clear fault. Potential overtrust and classification/reporting effects noted; no downstream harm or exploit demonstrated.',
'- Likelihood: Observed once per fixed input; wider failure frequency unmeasured.',
'- Severity: Informational observations; no vulnerability severity assigned. Application High priority is not audit severity.',
'- Technical Explanation: Repeated tokens collapse before BM25/embeddings; adding one VPN token still changes semantic scores. Category rule ties favor earlier VPN; full canonical query still retrieves printer evidence. Approved top score is weighted hybrid plus 0.26 metadata, so it exceeds one.',
'- Recommended Mitigation: Evaluate category/priority handling of unrelated terms, consistent nonprobabilistic score display and clarification for sparse ambiguous input. Preserve tested normalization. No application change applied.',
'- Conclusion: Primary relevance and answer grounding preserved for this fixed variant. No single-VPN causal control, live Groq result, general robustness, OS-specific repair correctness or IR-06 result claimed.',
]
path=AUDIT/'test_results.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-05 through IR-15 remain Not run.','IR-05 passed its controlled retrieval/fallback comparison; exploratory behavior is recorded separately. IR-06 through IR-15 remain Not run.',1)
text=re.sub(r'^\| IR-05 \|.*$',f'| IR-05 | Retrieval manipulation | Completed (controlled pair; exploration separate) | [{REL}/notes.md]({REL}/notes.md) | PASS (controlled pair) | NO demonstrated; Informational observations |',text,flags=re.M)
text,count=re.subn(r'^## IR-05[^\n]*\n.*?(?=^## IR-06)',lambda m:'\n'.join(record)+'\n\n',text,flags=re.M|re.S); assert count==1
write(path,text)
path=AUDIT/'test_plan.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-05 through IR-15 remain Not run.','IR-05 passed its controlled retrieval/fallback comparison; exploratory behavior is recorded separately. IR-06 through IR-15 remain Not run.',1)
text=re.sub(r'^\| IR-05 \|.*$',f'| IR-05 | Retrieval manipulation: repetition | Completed (controlled pair; exploration separate) | [{REL}/notes.md]({REL}/notes.md) | PASS (controlled pair) | NO demonstrated; Informational observations |',text,flags=re.M)
write(path,text)
path=AUDIT/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('the completed IR-01, IR-02 and IR-04 cases','the completed IR-01, IR-02, IR-04 and IR-05 cases')
text=text.replace('- evidence/IR-01/ through evidence/IR-04/: actual retrieval and unsupported-query evidence; IR-05 through IR-15 remain reserved.','- evidence/IR-01/ through evidence/IR-05/: actual retrieval, unsupported-query and keyword-stuffing evidence; IR-06 through IR-15 remain reserved.')
text=text.replace('IR-05 through IR-15 remain Not run.',f'IR-05 passed the fixed clear-printer comparison, with classification/display observations and exploratory limits; see [{REL}/notes.md]({REL}/notes.md). IR-06 through IR-15 remain Not run.')
write(path,text)
path=AUDIT/'evidence'/'README.md'; text=path.read_text(encoding='utf-8')
text=text.replace('IR-05/ through IR-15/ contain placeholders only.',f'IR-05/{RUN.name}/ contains baseline, fixed variant and separate exploratory evidence; the controlled pair passed. IR-06/ through IR-15/ contain placeholders only.')
write(path,text)
path=AUDIT/'vulnerability_register.md'; text=path.read_text(encoding='utf-8')
if '## IR-05 review' not in text:
    text+=f'\n## IR-05 review\n\nThe controlled IR-05 comparison passed: supported printer advice survived the fixed repeated-VPN variant. No VULN entry is created. OBS-IR05-01 records category/priority sensitivity; OBS-IR05-02 records unbounded scores displayed as 113%/107% while explanations cap at 100%. These are Informational observations with no demonstrated exploit or downstream harm. The separate ambiguous exploratory input produced mixed confident advice without clarification and repeated OBS-IR01-01 source-label wording; its intent is not sufficiently specified to prove displacement of a known printer fault. It is not reported as successful ambiguity handling. See [{REL}/notes.md]({REL}/notes.md).\n'
write(path,text)
path=AUDIT/'commands.md'; text=path.read_text(encoding='utf-8')
if '## IR-05 reproduction' not in text:
    text+=f'\n## IR-05 reproduction after explicit case authorization\n\n~~~powershell\n.\\.venv\\Scripts\\python.exe -B audit\\scripts\\run_ir05.py\n~~~\n\nRuns the planned baseline, appended-VPN variant and separately labelled exploratory phrase once each on independent synthetic databases with identical corpus/settings. Saves original analysis, normalization, ranking, answer and HTML under three subdirectories of a new IR-05 run. It does not execute IR-06 or later cases. The completed [{REL}/notes.md]({REL}/notes.md) can be read without rerunning.\n'
write(path,text)
path=AUDIT/'viva_notes.md'; text=path.read_text(encoding='utf-8')
if '## IR-05 observed result' not in text:
    text+='\n## IR-05 observed result\n\nThe controlled keyword-stuffing pair passed retrieval and fallback grounding: adding VPN five times to a clear printer-queue query retained KB-005 and the same three relevant citations, without VPN repair advice. Actual preprocessing collapsed five VPN tokens to one. This does not measure a repetition-only effect because no single-VPN control was run.\n\nTwo caveats matter: the category still changed from Printers to VPN and priority from Medium to High; the page displayed uncalibrated scores as 113%/107%. The short exploratory phrase produced mixed printer/VPN advice at HIGH 0.8783345915 without clarification. It lacks a clear fault, so it cannot establish wrong-intent displacement or successful ambiguity handling. Groq was disabled throughout.\n'
write(path,text)
assert all(hashes(AUDIT/'evidence'/name)==before for name,before in prior.items())
current=hashes(RUN)
assert all(current[name]==value for name,value in raw_before.items())
print('IR-05 controlled-pair PASS recorded; exploratory result separate; all original evidence preserved; IR-06 through IR-15 unexecuted.')