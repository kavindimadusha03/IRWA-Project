"""Record the reviewed result for the fixed IR-01 evidence run, not a new execution."""
from pathlib import Path
from datetime import datetime, timezone
import json
import re
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/"audit"
RUN=AUDIT/"evidence"/"IR-01"/"run-20260921T194038486465Z"
REL=RUN.relative_to(AUDIT).as_posix()
def read(name):
    return json.loads((RUN/name).read_text(encoding="utf-8"))
def write(path,text):
    path.write_text(text.strip()+"\n",encoding="utf-8")
execution=read("execution.json")
retrieval=read("retrieval.json")
solution=read("solution.json")
ticket=read("ticket.json")
process=read("process_result.json")
raw={item["source_id"]:item for item in read("hybrid_before_trust.json")}
assert execution["ticket_requests"]==1 and execution["http"]["ticket_page"]==200
assert ticket["description"]=="My laptop is connected to Wi-Fi but there is no internet."
assert retrieval["items"][0]["source_id"]=="SYN-0138"
assert not execution["llm"]["configured_enabled"] and execution["llm"]["successful_chat_returns"]==0
review={
    "review_recorded_at_utc":datetime.now(timezone.utc).isoformat(),
    "case":"IR-01","status":"Completed","outcome":"PASS","vulnerability_identified":"NO",
    "scope":"One normal end-to-end ticket on the isolated synthetic corpus, with the configured LLM disabled and its fallback observed.",
    "rationale":"The first source addresses the exact symptom; all five results concern connected Wi-Fi with no internet and have approved/resolved status. The displayed fallback reproduces the first three evidence contents without inventing additional troubleshooting actions.",
    "diagnostic_not_used_as_verdict":"top_in_pre_reviewed_relevant_KB_set=false because the top result is an eligible resolved historical ticket. The predeclared criteria allow resolved sources and do not require an approved KB article to rank first.",
    "observation":"OBS-IR01-01: template calls the top resolved ticket approved guidance. Recorded as an Informational transparency observation, not an established exploitable vulnerability.",
    "limits":["No live Groq generation was tested","No claim about overall retrieval metrics or OS-specific correctness","One observed query, no statistical confidence calibration","No claim that the earlier full-suite/evaluation memory failures are resolved in all runs"],
}
write(RUN/"review.json",json.dumps(review,indent=2,ensure_ascii=False))
notes=[
"# IR-01 - Exact Known Issue Retrieval","",
"**Outcome: PASS for this single-query retrieval and evidence-fallback scenario.** No security vulnerability is demonstrated by this case. The provenance wording observation below remains relevant for later source-reliability testing.","",
"## Objective and expected result","",
"Establish whether the ordinary ticket workflow retrieves evidence for a known issue. This is necessary before comparing manipulated or paraphrased queries.",
"",
"Title: Wi-Fi connected but no internet",
"",
"Description: My laptop is connected to Wi-Fi but there is no internet.",
"",
"The expected_result.md and source_preflight.json files were saved before the worker ran. Expected behavior: the top evidence addresses the symptom; returned sources have approved/resolved eligibility; any recommended actions are supported by relevant evidence. A HIGH score alone is not a pass.",
"",
"## Preconditions, exact steps and actual response","",
"- Verified the recorded private Phase 1 backup by checksum. No production rows were copied into the runtime corpus.",
"- Application/data/evaluation/test source hashes matched the Phase 1 snapshot.",
"- Used the unmodified synthetic CSVs: 80 KB articles and 500 historical tickets in a temporary SQLite database.",
"- Used cached all-MiniLM-L6-v2 with one numerical-library thread. No OS settings, ranking weights, thresholds, password hashing or application files were changed.",
f"- MiniLM loaded in {execution['model_preflight']['elapsed_seconds']} seconds. This is model preflight duration, not a cache speed comparison.",
"- Logged in normally with the seeded synthetic CUSTOMER account. No password, JWT or cookie value is recorded.",
f"- Login returned {execution['http']['login']['status']} to /home; authenticated /home returned {execution['http']['home']}.",
f"- Submitted exactly one POST to {execution['endpoint'].removeprefix('POST ')}.",
f"- Ticket submission returned {execution['http']['ticket_create']['status']} to /tickets/501; the resulting page returned {execution['http']['ticket_page']}.",
f"- Actual ticket URL during the run: {execution['ticket_url']}. The isolated server was stopped after evidence capture.",
f"- Category: {ticket['category']}. Canonical issue: {ticket['canonical_issue']}",
f"- Decision: {retrieval['decision']}; best adjusted score: {retrieval['best_score']:.10f}.",
f"- Ticket status: {ticket['status']}; approval status: {ticket['approval_status']}.",
f"- Retrieval function duration with the model already loaded: {execution['retrieval_elapsed_seconds']} seconds. Full helper duration: {process['elapsed_seconds']} seconds.",
"- Groq was disabled in the loaded configuration. Both LLM attempts raised RuntimeError; successful generated answers: zero. Ticket analysis used its rules and the solution used evidence-text fallback.",
"",
"Command actually executed (PowerShell, project root):",
"",
"~~~powershell",
r".\.venv\Scripts\python.exe -B audit\scripts\run_ir01.py",
"~~~",
"",
"This is a reproduction command, not a request to execute IR-01 again. A future run creates a new timestamped evidence folder rather than overwriting this one.",
"",
"## Actual ranking","",
"| Rank | Source | Type/status | BM25 | Semantic | Hybrid before trust | Adjusted score |",
"|---|---|---|---|---|---|---|",
]
for index,item in enumerate(retrieval["items"],1):
    notes.append(f"| {index} | {item['source_id']} | {item['source_type']} / {item['status']} | {item['bm25_score']:.6f} | {item['semantic_score']:.6f} | {raw[item['source_id']]['hybrid_score']:.6f} | {item['hybrid_score']:.6f} |")
notes += [
"",
"All five returned sources describe connected Wi-Fi with unavailable internet or websites failing to load. SYN-0138 is a relevant resolved historical ticket; KB-001 is the approved DNS recovery article. A relevant historical ticket ranking first is permitted by the recorded expectations.",
"",
"The helper's extra check top_in_pre_reviewed_relevant_KB_set is false. It only asks whether the first ID belongs to the pre-reviewed KB subset; it is not the overall verdict and does not exclude relevant historical tickets. No expected criterion was changed after execution.",
"",
"## Recommendation-to-source review","",
"| Displayed content/action | Supporting source | Assessment |",
"|---|---|---|",
"| Restart the network adapter and flush DNS, described as a previous resolution | SYN-0138 and SYN-0033 | Present verbatim in both resolved-ticket evidence bodies; same reported connectivity symptom |",
"| Open Command Prompt and run ipconfig /flushdns; reconnect to Wi-Fi and test | KB-001 | Present verbatim in the approved article for the same symptom |",
"| Historical macOS and Windows 11 context | SYN-0138 and SYN-0033 respectively | Labelled as separate evidence records; not newly invented facts about this customer |",
"",
"The fallback contains the first three source bodies. It does not add novel troubleshooting steps. This passes the recorded grounding expectation at the evidence-text level. The user did not specify an operating system: the mixed-platform evidence is not proof that every step applies to every platform. No real device repair was performed.",
"",
"## Technical explanation","",
"The top source has normalized BM25 1.0 and semantic 0.6452382641. With the unchanged weights, the hybrid score before trust is 0.8048810452. Resolved-ticket trust multiplies it by 0.85; category/status bonuses total 0.26, producing 0.9441488885. This exceeds the configured HIGH boundary 0.68.",
"",
"The source is relevant by its content, not because it has a high score. The displayed 94% is derived from a heuristic score and is not a probability of a correct solution.",
"",
"recommend_solution() falls back to the combined evidence text after llm.chat() raises. Therefore this run demonstrates retrieval and fallback grounding, not successful LLM generation or general hallucination resistance.",
"",
"## OBS-IR01-01 - provenance wording","",
"Observed behavior: the explanation and suggested reply call SYN-0138 approved guidance, while retrieval.json and ticket.json identify it as a resolved_ticket.",
"",
"Technical reason: app/agents/solution_agent.py:38-40 and :60-62 use unconditional approved-guidance wording rather than checking source_type/status. The evidence also spans different platforms while retrieved supported_os is Any.",
"",
"Impact: the wording can overstate source approval and encourage overtrust. No incorrect novel action, disclosure, privilege escalation or observed harm was demonstrated in this case.",
"",
"Likelihood: observed in this one run; the wording branch is used when a resolved ticket ranks first. A population-level likelihood has not been measured.",
"",
"Severity: Informational observation. No exploitable vulnerability severity is assigned.",
"",
"Recommended mitigation: use source-aware wording such as resolved historical ticket versus approved KB article; preserve relevant OS context and explain the score as a ranking measure. Do not apply the change before finishing the baseline assessment. Revisit trust/provenance in IR-10 and grounding in IR-11.",
"",
"Ticket priority Critical is an application triage label. It is not this audit's vulnerability severity.",
"",
"## Evidence and limits","",
"- input.txt: exact ticket input.",
"- expected_result.md: predeclared acceptance criteria.",
"- source_preflight.json: relevant approved article bodies and CSV hashes.",
"- preconditions.json: configuration/isolation and private backup verification.",
"- execution.json: unmodified worker observations; its Unassessed value preceded this separate review.",
"- hybrid_before_trust.json and retrieval.json: captured returns from the single original retrieval call.",
"- solution.json and ticket.json: actual fallback, explanation, stored status and citations.",
"- customer_result.html: actual captured HTTP response, with secret-value redaction; not an invented screenshot.",
"- terminal_log.txt: actual process/server output.",
"- process_result.json: one ticket request, exit 0, unchanged source and original database main-file hashes.",
"- review.json: this reviewed PASS verdict and limits.",
"",
"No screenshot was created. The historical runtime URL is no longer serving this isolated instance; inspect customer_result.html or the JSON/logs for the saved result.",
"",
"Original database main-file checksums do not cover possible concurrent WAL activity by another application instance. This helper does not write the original database.",
"",
"Conclusion: IR-01 passes for the observed synthetic known-issue retrieval/fallback path. IR-02 through IR-15 were not executed. Earlier Phase 1 failed runs remain preserved and are not rewritten as passing."
]
write(RUN/"notes.md","\n".join(notes))
record=[
"## IR-01 - Exact Known Issue Retrieval","",
"- Test ID: IR-01",
"- Test Name: Exact Known Issue Retrieval",
"- Test Objective: Verify that a normal known Wi-Fi/no-internet issue retrieves relevant evidence through the complete ticket workflow.",
"- Component Being Tested: create_ticket(), process_new_ticket(), analyze_ticket(), search_knowledge(), hybrid_rank(), recommend_solution(), and the ticket result page.",
"- Input / Attack Scenario: Title: Wi-Fi connected but no internet. Description: My laptop is connected to Wi-Fi but there is no internet. This was a normal positive case, not an attack.",
"- Preconditions: Verified private backup; isolated synthetic SQLite data (80 KB, 500 historical tickets); active CUSTOMER; MiniLM loaded; weights 0.45/0.55 and thresholds 0.68/0.55 unchanged; Groq disabled.",
"- Steps: Save input/expectations and source preflight; load model; seed isolated DB; start reserved localhost server; log in; submit exactly one ticket; capture returned ranking/solution and stored ticket/page; stop server; compare evidence.",
"- Expected Behaviour: Top evidence addresses the exact symptom; eligible approved/resolved sources; recommended actions supported by relevant retrieved evidence.",
f"- Actual Behaviour: Login 303 and authenticated home 200; one ticket submitted, redirect to /tickets/501 and page 200; top SYN-0138, approved KB-001 third; HIGH {retrieval['best_score']:.10f}; SOLUTION_PROPOSED / PENDING. Model loaded successfully on this run.",
f"- Evidence: [{REL}/notes.md]({REL}/notes.md), with input, expected result, source preflight, original return-value JSON, stored ticket, captured HTML and terminal log.",
"- Observation: All five results address the symptom. Fallback reproduces three source bodies; live Groq generation was not observed. Top resolved ticket is incorrectly called approved guidance in the explanation.",
"- Outcome: PASS (single-query retrieval and evidence-fallback scope).",
"- Vulnerability Identified: NO demonstrated security vulnerability in this case; see Informational provenance observation OBS-IR01-01.",
"- Impact: No retrieval-related security impact demonstrated; wording may overstate approval and create overtrust.",
"- Likelihood: No exploit likelihood established; misleading wording was observed once when a resolved ticket ranked first.",
"- Severity: No vulnerability severity assigned. OBS-IR01-01 is Informational. Ticket priority Critical is not an audit severity.",
"- Technical Explanation: Top BM25=1.0, semantic=0.6452382641; base hybrid=0.8048810452, resolved trust=0.85 plus metadata=0.26 gives 0.9441488885. Application's configured LLM fallback returns evidence text.",
"- Recommended Mitigation: No retrieval fix is justified solely by this passing case. For OBS-IR01-01, make source-approval wording accurate and preserve OS context; no application fix applied.",
"- Conclusion: Relevant known-issue evidence and grounded fallback observed. No claim of live LLM correctness, all-platform applicability, overall retrieval metrics, or that the full earlier baseline suite now passes.",
]
results=AUDIT/"test_results.md"
text=results.read_text(encoding="utf-8")
text=text.replace("These are unexecuted case records, not baseline unit-test results. See baseline.md for the separate Phase 1 executions.","These are individual audit-case results and pending case records. IR-01 is completed; IR-02 through IR-15 remain Not run. See baseline.md for the separately preserved Phase 1 executions.")
text=re.sub(r"^\| IR-01 \|.*$",f"| IR-01 | Retrieval accuracy | Completed (fallback mode) | [{REL}/notes.md]({REL}/notes.md) | PASS | NO demonstrated; Informational observation recorded |",text,flags=re.M)
text=re.sub(r"^## IR-01[^\n]*\n.*?(?=^## IR-02)",lambda m:"\n".join(record)+"\n\n",text,flags=re.M|re.S)
write(results,text)
plan=AUDIT/"test_plan.md"
text=plan.read_text(encoding="utf-8")
text=text.replace("This is a plan for the 15 core audit cases, not a record of their execution. All 15 cases are Not run. No PASS, FAIL, vulnerability, severity, metric result, timing, or screenshot is claimed for these cases.","This file preserves the predeclared plan for the 15 core audit cases. IR-01 has now been executed and reviewed; its actual evidence and scoped PASS are in test_results.md. IR-02 through IR-15 remain Not run.")
text=re.sub(r"^\| IR-01 \|.*$",f"| IR-01 | Retrieval accuracy: exact issue | Completed (fallback mode) | [{REL}/notes.md]({REL}/notes.md) | PASS | NO demonstrated; Informational observation recorded |",text,flags=re.M)
write(plan,text)
readme=AUDIT/"README.md"
text=readme.read_text(encoding="utf-8")
text=text.replace("This workspace records Phase 1 preparation and actual baseline attempts.","This workspace records Phase 1 preparation, actual baseline attempts and the completed IR-01 case.")
text=text.replace("- evidence/IR-01/ through evidence/IR-15/: reserved evidence directories.","- evidence/IR-01/: actual known-issue test evidence; IR-02 through IR-15 remain reserved.")
text=text.replace("The 15 audit cases are still Not run. Normal baseline checks do not count as IR-01, IR-13 or another completed security test. Stop after Phase 1 and wait for “Continue to IR-01”.",f"IR-01 passed in the configured fallback mode: model loading, normal login and one known-query ticket succeeded. See [{REL}/notes.md]({REL}/notes.md). IR-02 through IR-15 remain Not run. No later case will run until requested. Phase 1 failures remain preserved; this one successful run does not replace the earlier test suite or IR evaluation results.")
write(readme,text)
write(AUDIT/"evidence"/"README.md",f"""# Evidence index

baseline/ preserves actual Phase 1 observations and failed runs. Its low_memory/ directory contains the separately labelled reduced-thread attempts.

IR-01/{RUN.name}/ contains the actual single-ticket run, its predeclared expectations, captured responses and separate reviewed PASS verdict. The case used synthetic data and the configured LLM fallback.

IR-02/ through IR-15/ contain placeholders only. No screenshot was fabricated; customer_result.html is the actual saved HTTP response, not a screenshot.

Private backups and temporary databases are outside the repository. Never add keys, passwords, cookies, JWTs or .env contents.
""")
register=AUDIT/"vulnerability_register.md"
text=register.read_text(encoding="utf-8")
if "IR-01 review" not in text:
    text+=f"\n## IR-01 review\n\nIR-01 passed within its single-query/fallback scope. No VULN entry is created. OBS-IR01-01 records misleading approved-guidance wording for a resolved historical ticket as an Informational transparency observation; see [{REL}/notes.md]({REL}/notes.md). Its exploitation or harmful impact has not been established.\n"
write(register,text)
commands=AUDIT/"commands.md"
text=commands.read_text(encoding="utf-8")
if "## IR-01 reproduction" not in text:
    text+=f"""
## IR-01 reproduction after explicit case authorization

~~~powershell
python -B audit/scripts/run_ir01.py
~~~

This loads the cached model, seeds a new temporary synthetic database, logs in using the seeded CUSTOMER, submits exactly one normal Wi-Fi ticket, captures unmodified return values and the HTTP ticket page, and stops its own server. Every run saves a new timestamped folder beneath evidence/IR-01/. It does not rerun the 15 cases.

The recorded case is [{REL}/notes.md]({REL}/notes.md). Read it before deciding to rerun anything. Phase 1 failures are historical records, and the Phase 1 report renderer must not be rerun to reset completed test records.
"""
write(commands,text)
viva=AUDIT/"viva_notes.md"
text=viva.read_text(encoding="utf-8")
if "## IR-01 observed result" not in text:
    text+="""
## IR-01 observed result

Short answer: the known Wi-Fi issue retrieved relevant evidence and passed in fallback mode. The best result was a resolved historical ticket, SYN-0138, and the approved article KB-001 ranked third.

Follow-up: the final ranking score was 0.9441488885 and the system proposed a solution pending approval. Groq was disabled, so the answer reproduced retrieved evidence rather than being generated by an LLM. This does not prove 94% correctness or broad retrieval accuracy. The explanation's approved-guidance wording overstated the top source's status; that is recorded as an Informational observation rather than an invented exploit.
"""
write(viva,text)
print("Recorded IR-01 PASS (fallback scope), preserved raw observations, and left IR-02 through IR-15 unexecuted.")
