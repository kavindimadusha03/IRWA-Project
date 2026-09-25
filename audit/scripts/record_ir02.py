"""Record reviewed IR-02 only from preserved actual evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,re
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"audit"
RUN=AUDIT/"evidence"/"IR-02"/"run-20260921T200014957237Z"
PREV=AUDIT/"evidence"/"IR-01"/"run-20260921T194038486465Z"
REL=RUN.relative_to(AUDIT).as_posix()
def read(folder,name): return json.loads((folder/name).read_text(encoding="utf-8"))
def write(path,text): path.write_text(text.strip()+"\n",encoding="utf-8")
e=read(RUN,"execution.json"); r=read(RUN,"retrieval.json"); s=read(RUN,"solution.json"); t=read(RUN,"ticket.json")
old=read(PREV,"retrieval.json"); ot=read(PREV,"ticket.json"); oe=read(PREV,"execution.json")
norm=read(RUN,"query_preprocessing.json")
raw={i["source_id"]:i for i in read(RUN,"hybrid_before_trust.json")}
assert e["ticket_requests"]==1 and e["http"]["ticket_page"]==200
assert e["comparison_to_IR01"]["same_configuration"]
assert r["items"][0]["source_id"]=="SYN-0027" and not e["llm"]["configured_enabled"]
comparison={
 "reference_case":"IR-01","reference_run":PREV.relative_to(ROOT).as_posix(),
 "current_case":"IR-02","current_run":RUN.relative_to(ROOT).as_posix(),
 "original_query":ot["description"],"paraphrased_query":t["description"],"actual_normalized_paraphrase":norm["normalized_query"],
 "same_configuration":e["comparison_to_IR01"]["same_configuration"],
 "corpus_and_source_hash_checks":read(RUN,"comparison_preflight.json"),
 "IR01":{"ranking":[x["source_id"] for x in old["items"]],"top_score":old["best_score"],"decision":old["decision"],"priority":ot["priority"]},
 "IR02":{"ranking":[x["source_id"] for x in r["items"]],"top_score":r["best_score"],"decision":r["decision"],"priority":t["priority"]},
 "same_top_five_set":{x["source_id"] for x in old["items"]}=={x["source_id"] for x in r["items"]},
 "relevance_review":"All five sources describe connected Wi-Fi with unavailable internet or websites failing to load; first-three evidence bodies support the displayed fallback actions.",
 "claim_limit":"Hybrid handling of this paraphrase, not semantic-only attribution, probability calibration or successful LLM generation."
}
write(RUN/"comparison.json",json.dumps(comparison,indent=2,ensure_ascii=False))
review={"review_recorded_at_utc":datetime.now(timezone.utc).isoformat(),"case":"IR-02","status":"Completed","outcome":"PASS","vulnerability_identified":"NO","scope":"One end-to-end paraphrased ticket on unchanged synthetic corpus/settings, with configured LLM disabled and fallback observed.","rationale":"Same five relevant eligible sources as IR-01, changed ordering; displayed fallback copies supported first-three evidence without novel steps.","observations":["OBS-IR02-01: metadata category bonus differs between equivalent query wordings","OBS-IR01-01 recurs: resolved historical ticket called approved guidance","Application triage priority changes from Critical to Medium; not an audit vulnerability severity"],"limits":["No semantic-only causality claim; leading source closely matches query lexically","No live Groq generation","Operating system unspecified; platform-specific correctness not tested","No aggregate evaluation metrics recomputed"]}
write(RUN/"review.json",json.dumps(review,indent=2,ensure_ascii=False))
notes=[
"# IR-02 - Paraphrased Query Retrieval","",
"**Outcome: PASS for this single paraphrase through the full retrieval/evidence-fallback workflow.** No security vulnerability is demonstrated by this case.","",
"## Why and what we tested","",
"IR-01 established retrieval for a directly worded Wi-Fi/no-internet issue. IR-02 changes the description while preserving its meaning, to check whether relevant evidence and supported advice remain available.",
"",
"Title: Wireless connected but websites will not load",
"",
"Description: My wireless connection shows connected but websites will not load.",
"",
"The expected_result.md was written before execution. Source order and numeric scores were allowed to change; a category label or HIGH score alone was not sufficient. The same approved KB and resolved-ticket sources remained eligible.",
"",
"## Preconditions and exact steps","",
"- Compared application/data/evaluation/test source hashes and both CSV hashes with IR-01: unchanged.",
"- Verified the recorded private backup by checksum; original working-database rows were not used as runtime fixtures.",
"- Used a fresh temporary SQLite database seeded from 80 synthetic KB articles and 500 historical tickets.",
"- Loaded the same cached MiniLM model, with one numerical-library thread; weights 0.45/0.55, thresholds 0.68/0.55 and top-k 5 matched IR-01.",
"- Confirmed the same Groq mode: disabled. No key or credential value was recorded.",
"- Started a server on a reserved loopback socket, logged in normally as the seeded synthetic CUSTOMER, then submitted exactly one ticket.",
"- Observed original normalization, hybrid, retrieval and solution return values without altering arguments or results.",
"- Saved the actual HTTP ticket page, stopped the audit server, and checked source/original-database main-file hashes.",
"",
"Exact command used in the project PowerShell terminal:",
"",
"~~~powershell",r".\.venv\Scripts\python.exe -B audit\scripts\run_ir02.py","~~~",
"",
"This is a reproduction command, not a request to repeat the case. Any rerun creates a new evidence directory.",
"",
f"Actual page/endpoint during execution: {e['page']} -> {e['endpoint']}. Ticket URL: {e['ticket_url']}. The isolated server is now stopped.",
"",
f"Observed HTTP results: login {e['http']['login']['status']} to /home; home {e['http']['home']}; ticket submission {e['http']['ticket_create']['status']} to /tickets/501; ticket page {e['http']['ticket_page']}.",
"",
"## Actual comparison","",
"| Property | IR-01 | IR-02 |","|---|---|---|",
f"| Top source | {old['items'][0]['source_id']} | {r['items'][0]['source_id']} |",
f"| Best adjusted score | {old['best_score']:.10f} | {r['best_score']:.10f} |",
f"| Decision | {old['decision']} | {r['decision']} |",
f"| Category | {ot['category']} | {t['category']} |",
f"| Ticket status | {ot['status']} | {t['status']} |",
f"| Approval | {ot['approval_status']} | {t['approval_status']} |",
f"| Application triage priority | {ot['priority']} | {t['priority']} |",
"| Groq | Disabled; fallback | Disabled; fallback |",
"",
"| IR-02 rank | Source | IR-01 rank | Type/status | BM25 | Semantic | Adjusted score |",
"|---|---|---|---|---|---|---|"]
old_ranks={item["source_id"]:idx for idx,item in enumerate(old["items"],1)}
for idx,item in enumerate(r["items"],1):
 notes.append(f"| {idx} | {item['source_id']} | {old_ranks[item['source_id']]} | {item['source_type']} / {item['status']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {item['hybrid_score']:.6f} |")
notes += [
"",
"All five sources from IR-01 remain in the top five. SYN-0027 directly describes a wireless icon showing connected while websites do not load. KB-001, now second, contains the approved DNS-cache recovery guidance. The other resolved tickets describe the same symptom.",
"",
"The diagnostic top_in_pre_reviewed_relevant_KB_set=false is not a failure: the top result is an eligible resolved historical ticket, and the planned expectation does not require a KB article to rank first.",
"",
"## Query preprocessing and limits on semantic claims","",
f"Actual canonical issue: {t['canonical_issue']}",
"",
f"Actual normalized query: {norm['normalized_query']}",
"",
"The captured normalization maps wireless to wifi and removes the filler my. BM25 and embeddings both receive that normalized query. The leading source's wording is also very close to the paraphrase and has normalized BM25 1.0. Therefore success cannot be attributed to embeddings alone. It demonstrates this combined pipeline's handling of this particular paraphrase.",
"",
"## Grounding review","",
"| Displayed action/content | Supporting retrieved evidence | Assessment |",
"|---|---|---|",
"| Restart network adapter and flush DNS, described as historical resolution | SYN-0027 and SYN-0033 | Present verbatim in resolved-ticket bodies for the same symptom |",
"| Run ipconfig /flushdns; reconnect to Wi-Fi and test | KB-001 | Present verbatim in the approved article |",
"| Windows 10 and Windows 11 contexts | SYN-0027 and SYN-0033 respectively | Historical source contexts, not new claims about this customer's device |",
"",
"The configured LLM was disabled: two attempts raised RuntimeError and no chat returned successfully. The final answer copies the first three evidence bodies. No novel troubleshooting steps were added. This establishes fallback evidence support, not live generated-answer correctness. The user's OS is unspecified; no platform-specific applicability or actual repair success is established.",
"",
"## Technical explanation and observations","",
"Top score: (0.45 x 1.0 + 0.55 x 0.7734548893) x 0.85 + 0.08 = 0.8240901608. This exceeds HIGH=0.68.",
"",
"OBS-IR02-01 (Informational scoring-consistency observation): metadata boosting checks the original canonical query, not the query produced by normalize_query_for_search(). The original wireless phrasing lacks the literal category-token match that gave IR-01 +0.18. Both cases receive +0.08 for approved/resolved status; IR-01's total metadata bonus was +0.26, while IR-02's is +0.08. Evidence: query_preprocessing.json, captured scores and app/agents/retrieval_agent.py:17-40,94-110.",
"",
"Impact: equivalent wording can alter confidence through the metadata bonus as well as changing lexical/semantic scores. Both actual cases remained HIGH and relevant, so no harmful decision or exploitable vulnerability is established here. Likelihood: demonstrated for this pair only; broader frequency and threshold effects remain unmeasured.",
"",
"Recommended mitigation to evaluate later: normalize query terms and category labels consistently, then validate confidence decisions against labelled cases. Feeding only a normalized query into the unchanged category matcher is not necessarily sufficient because category token spelling/spacing also matters. No fix was applied.",
"",
"OBS-IR01-01 recurs: the explanation calls resolved-ticket SYN-0027 approved guidance. This repeats the existing Informational provenance wording observation, not a new vulnerability. Prefer source-aware wording after documenting baseline behavior.",
"",
"The application triage priority changed from Critical in IR-01 to Medium in IR-02. The rule-based classifier's literal no internet trigger occurs only in IR-01. This is a triage observation outside the IR-02 relevance verdict, and those words are not audit vulnerability severities.",
"",
"The lower final score does not mean a measured reduction in correctness. Ranking scores are not calibrated probabilities.",
"",
"## Evidence and scope","",
"- input.txt and expected_result.md: exact input and predeclared criteria.",
"- comparison_preflight.json: same-source and same-CSV checks.",
"- source_preflight.json and preconditions.json: source bodies, hashes and backup verification.",
"- query_preprocessing.json: exact captured original/normalized query.",
"- hybrid_before_trust.json and retrieval.json: actual original return values.",
"- solution.json, ticket.json and customer_result.html: actual fallback, citations, stored status and HTTP response.",
"- execution.json and terminal_log.txt: raw observations; worker verdict remained Unassessed until this separate review.",
"- process_result.json: one ticket, exit 0, original database main file and source hashes unchanged.",
"- comparison.json and review.json: reviewed comparison and scoped PASS.",
"",
f"Model-loading preflight: {e['model_preflight']['elapsed_seconds']} seconds. Retrieval with model already loaded: {e['retrieval_elapsed_seconds']} seconds. These are single observations, not a cache benchmark.",
"",
"No screenshot was fabricated; customer_result.html is a captured response. The two /tickets/501 IDs belong to different isolated databases, not the same persisted ticket or original working database.",
"",
"Conclusion: IR-02 passes within the single-query hybrid/fallback scope. IR-03 through IR-15 remain unexecuted. Phase 1 test-suite/evaluation failures and IR-01 evidence are preserved."
]
write(RUN/"notes.md","\n".join(notes))
record=[
"## IR-02 - Paraphrased Query Retrieval","",
"- Test ID: IR-02",
"- Test Name: Paraphrased Query Retrieval",
"- Test Objective: Verify that equivalent wording preserves relevant Wi-Fi/no-internet retrieval and evidence-supported advice.",
"- Component Being Tested: Ticket analysis, normalize_query_for_search(), BM25Search, semantic_scores(), hybrid_rank(), search_knowledge(), recommend_solution(), and ticket page.",
"- Input / Attack Scenario: Title: Wireless connected but websites will not load. Description: My wireless connection shows connected but websites will not load. Normal positive case.",
"- Preconditions: Same source/CSV hashes, same effective configuration and Groq-disabled mode as IR-01; verified backup; fresh synthetic SQLite corpus; cached MiniLM loaded; active CUSTOMER.",
"- Steps: Save expected result and comparison checks; seed isolated corpus; start localhost; log in normally; submit one paraphrased ticket; capture normalization, scores, answer, citations and HTML; compare against IR-01; stop server.",
"- Expected Behaviour: Relevant evidence remains available and any advice is supported; identical ranking or scores are not required.",
f"- Actual Behaviour: Login 303; home and ticket page 200; same five relevant sources in different order; top SYN-0027, KB-001 second; HIGH {r['best_score']:.10f}; SOLUTION_PROPOSED / PENDING.",
f"- Evidence: [{REL}/notes.md]({REL}/notes.md), with raw responses, normalized query, comparison.json, recorded expectations and actual HTML.",
"- Observation: wireless became wifi before BM25/embeddings. Metadata boosting used the original wording and omitted IR-01's +0.18 category bonus. Approved-guidance wording again overstated the top resolved source. Priority changed Critical to Medium.",
"- Outcome: PASS (single paraphrase, combined retrieval and evidence fallback).",
"- Vulnerability Identified: NO demonstrated security vulnerability; Informational scoring/provenance observations recorded.",
"- Impact: No harmful retrieval decision demonstrated; equivalent wording affects heuristic confidence and triage priority.",
"- Likelihood: Differences observed for this pair; broader frequency and exploitability unmeasured.",
"- Severity: No vulnerability severity assigned; scoring/provenance observations are Informational.",
"- Technical Explanation: Top BM25=1.0; semantic=0.7734548893; base hybrid=0.8754001891; resolved-source trust=0.85 and status bonus=0.08 produce 0.8240901608. Groq-disabled fallback copies retrieved evidence.",
"- Recommended Mitigation: No retrieval fix follows solely from the PASS. Evaluate consistent query/category normalization and accurate source labels later; no application change applied.",
"- Conclusion: Equivalent wording preserved relevant evidence. No claim of semantic-only causality, live LLM grounding, platform suitability, overall accuracy or resolved Phase 1 suite failures."
]
path=AUDIT/"test_results.md"; text=path.read_text(encoding="utf-8")
text=text.replace("IR-01 is completed; IR-02 through IR-15 remain Not run.","IR-01 and IR-02 are completed; IR-03 through IR-15 remain Not run.")
text=re.sub(r"^\| IR-02 \|.*$",f"| IR-02 | Semantic accuracy / paraphrase | Completed (hybrid/fallback mode) | [{REL}/notes.md]({REL}/notes.md) | PASS | NO demonstrated; Informational observations |",text,flags=re.M)
text=re.sub(r"^## IR-02[^\n]*\n.*?(?=^## IR-03)",lambda m:"\n".join(record)+"\n\n",text,flags=re.M|re.S);write(path,text)
path=AUDIT/"test_plan.md";text=path.read_text(encoding="utf-8")
text=text.replace("IR-01 has now been executed and reviewed; its actual evidence and scoped PASS are in test_results.md. IR-02 through IR-15 remain Not run.","IR-01 and IR-02 have been executed and reviewed; actual evidence and scoped PASS results are in test_results.md. IR-03 through IR-15 remain Not run.")
text=re.sub(r"^\| IR-02 \|.*$",f"| IR-02 | Retrieval accuracy: paraphrase | Completed (hybrid/fallback mode) | [{REL}/notes.md]({REL}/notes.md) | PASS | NO demonstrated; Informational observations |",text,flags=re.M);write(path,text)
path=AUDIT/"README.md";text=path.read_text(encoding="utf-8")
text=text.replace("the completed IR-01 case","the completed IR-01 and IR-02 cases")
text=text.replace("- evidence/IR-01/: actual known-issue test evidence; IR-02 through IR-15 remain reserved.","- evidence/IR-01/ and evidence/IR-02/: actual known-issue/paraphrase evidence; IR-03 through IR-15 remain reserved.")
text=text.replace("IR-02 through IR-15 remain Not run.",f"IR-02 also passed in hybrid/fallback mode; see [{REL}/notes.md]({REL}/notes.md). IR-03 through IR-15 remain Not run.")
write(path,text)
path=AUDIT/"evidence"/"README.md";text=path.read_text(encoding="utf-8")
text=text.replace("IR-02/ through IR-15/ contain placeholders only.",f"IR-02/{RUN.name}/ contains the actual paraphrase result and IR-01 comparison. IR-03/ through IR-15/ contain placeholders only.")
write(path,text)
path=AUDIT/"vulnerability_register.md";text=path.read_text(encoding="utf-8")
if "## IR-02 review" not in text:
 text+=f"\n## IR-02 review\n\nIR-02 passed for this paraphrase through combined retrieval/evidence fallback. No VULN entry is created. OBS-IR02-01 records metadata bonus differences for equivalent wording; OBS-IR01-01 source-label wording recurred. Both are Informational observations without demonstrated harmful impact or exploitation in this case. See [{REL}/notes.md]({REL}/notes.md).\n"
write(path,text)
path=AUDIT/"commands.md";text=path.read_text(encoding="utf-8")
if "## IR-02 reproduction" not in text:
 text+=f"""
## IR-02 reproduction after explicit case authorization

~~~powershell
python -B audit/scripts/run_ir02.py
~~~

This runs one paraphrased ticket on a fresh synthetic database, first checking source/CSV hashes and effective settings against IR-01. It saves normalized query, original returned scores, answer and HTTP page in a new IR-02 timestamped folder. See [{REL}/notes.md]({REL}/notes.md) for the already completed case; no rerun is needed to read the result. No other audit case is executed by this command.
"""
write(path,text)
path=AUDIT/"viva_notes.md";text=path.read_text(encoding="utf-8")
if "## IR-02 observed result" not in text:
 text+="""
## IR-02 observed result

Short answer: the paraphrased Wi-Fi query passed. It returned the same five relevant sources as IR-01 in a different order; SYN-0027 became first, KB-001 second, and the decision remained HIGH at 0.8240901608.

Follow-up: the system normalized wireless to wifi before both lexical and semantic scoring. The leading document also closely matched the paraphrase lexically. This test therefore supports hybrid paraphrase handling, not semantic-only performance. Groq was disabled and the answer was evidence fallback. Metadata boosting used the original wording and omitted the category bonus, showing why a lower heuristic score is not automatically a less correct result.
"""
write(path,text)
print("IR-02 PASS recorded; IR-01 raw evidence preserved; IR-03 through IR-15 remain unexecuted.")
