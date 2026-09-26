"""Safely rerun Student 4 IR-01..IR-15 against the *current* project checkout.

This launcher lives outside audit. It never deletes/overwrites prior audit files.
Start it from the project root. Legacy runners use ephemeral synthetic SQLite DBs.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve().parent
AUDIT = ROOT / 'audit'
CASE_NAMES = {
 'IR-01':'Exact known issue','IR-02':'Paraphrase','IR-03':'Technical error code',
 'IR-04':'Unknown issue / safe abstention','IR-05':'Keyword stuffing',
 'IR-06':'Conflicting categories','IR-07':'Bounded long noisy query',
 'IR-08':'Error-code formatting','IR-09':'Exclude draft KB',
 'IR-10':'Source trust','IR-11':'Answer grounding / hallucination',
 'IR-12':'Confidence thresholds','IR-13':'Anonymous agent access',
 'IR-14':'Role-based access','IR-15':'API validation and provenance',
}
PRECONDITIONS={
 'IR-02':['IR-01'],'IR-03':['IR-01'],'IR-04':['IR-01'],
 'IR-05':['IR-01'],'IR-06':['IR-01'],'IR-07':['IR-01','IR-05'],
 'IR-08':['IR-01','IR-03'],'IR-09':['IR-01'],'IR-10':['IR-01'],
 'IR-11':['IR-01'],'IR-12':['IR-01'],'IR-13':['IR-01'],'IR-14':['IR-01'],
 'IR-15':[],
}


def utc_stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def safe_text(text: str) -> str:
    """Best-effort log masking; don't pass real secrets as query/test inputs."""
    text = re.sub(r'(?im)^(\s*(?:GROQ_API_KEY|SECRET_KEY|AUTHORIZATION|PASSWORD|ACCESS_TOKEN)\s*[:=]\s*)[^\r\n]+', r'\1[REDACTED]',text)
    text = re.sub(r'(?i)\b(?:gsk_[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9_.-]{12,})\b','[REDACTED]',text)
    return text


def run_step(label, command, output_dir, env, timeout):
    print(f'\n[START] {label}',flush=True)
    began=time.monotonic()
    try:
        done=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        status=done.returncode
        log=safe_text(done.stdout+'\n'+done.stderr)
        timeout_hit=False
    except subprocess.TimeoutExpired as exc:
        def decode(value):
            return value.decode('utf-8','replace') if isinstance(value,bytes) else (value or '')
        status=None
        log=safe_text(decode(exc.stdout)+'\n'+decode(exc.stderr)+'\nTimed out by local launcher.')
        timeout_hit=True
    elapsed=round(time.monotonic()-began,2)
    if output_dir is not None:
        output_dir.mkdir(parents=True,exist_ok=True)
        (output_dir / (label.replace(' ','_').replace('/','-')+'.log')).write_text(log,encoding='utf-8')
    # Present bounded output without exposing a huge log on screen.
    print('\n'.join(log.strip().splitlines()[-13:])[-2400:],flush=True)
    print(f'[END] {label}: '+ ('TIMEOUT' if timeout_hit else ('EXIT 0' if status==0 else f'EXIT {status}')) + f' ({elapsed}s)',flush=True)
    return {'step':label,'command':[str(x) for x in command[1:]],'exit_code':status,'timed_out':timeout_hit,'seconds':elapsed}


def mode_env(enable_live_llm=False):
    env=dict(os.environ)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        env[key]='1'
    env['HF_HUB_OFFLINE']='1'; env['TRANSFORMERS_OFFLINE']='1'
    env['PYTHONDONTWRITEBYTECODE']='1'
    if not enable_live_llm:
        env['GROQ_API_KEY']=''
    return env


def require_project(require_working_db=False):
    missing=[str(p) for p in [ROOT/'app'/'main.py',ROOT/'data'/'knowledge_base.csv',
                                  ROOT/'data'/'tickets.csv',ROOT/'evaluation'/'gold_queries.csv',
                                  ROOT/'requirements.txt'] if not p.exists()]
    if require_working_db and not (ROOT/'knowgap.db').is_file():
        missing.append('knowgap.db (original audit helpers need to snapshot/verify it)')
    if missing:
        raise SystemExit('Missing project files: '+', '.join(missing)+'\nCopy irwa_retest into the same root as app/, data/, evaluation/, knowgap.db.')


def render_report(logdir,results,live):
    result={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'mode':'optional original Groq configuration' if live else 'provider disabled for deterministic retest',
            'qualification':'Exit 0 means collection completed, not that security/retrieval assertions PASS. Review evidence/expected_result.md and actual responses.',
            'results':results}
    (logdir/'suite_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# IRWA retest execution status','',
           '**Execution status is not an academic PASS/FAIL conclusion.** Review saved response/source evidence and document each finding independently.','',
           f"Provider mode: {result['mode']}",'',
           '| Step | Process result | Time (s) | Evidence |','|---|---|---:|---|']
    for row in results:
        evidence='`audit/evidence/'+row['step']+'`' if row['step'].startswith('IR-') else '`audit/evidence/baseline`'
        status='TIMEOUT' if row['timed_out'] else ('COLLECTED (review needed)' if row['exit_code']==0 else ('SKIPPED / BLOCKED' if row['exit_code'] is None else f"ERROR ({row['exit_code']})"))
        lines.append(f"| {row['step']} | {status} | {row['seconds']} | {evidence} |")
    lines += ['', 'For each IR case, inspect the newest `audit/evidence/IR-NN/run-*/` folder, `expected_result.md`, `execution.json`, `process_result.json`, and actual response files. An execution error is *Inconclusive* until its cause is determined. Historical vulnerabilities are not automatically current.','']
    (logdir/'suite_summary.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\nSUMMARY: '+str(logdir/'suite_summary.md'),flush=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    actions=parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--list',action='store_true',help='Show all case IDs and execution order')
    actions.add_argument('--quick',action='store_true',help='Run 15 offline regressions in an isolated DB (no embedding download)')
    actions.add_argument('--full',action='store_true',help='Fresh baseline, original tests/evaluation, and all 15 original bounded runners')
    actions.add_argument('--all',action='store_true',help='Run quick tests and full retest sequentially')
    actions.add_argument('--case',choices=tuple(CASE_NAMES),help='Rerun a single original case after fresh baseline and prerequisites')
    parser.add_argument('--dry-run',action='store_true',help='Check planned actions only; do not execute tests')
    parser.add_argument('--allow-live-llm',action='store_true',help='Opt-in to existing Groq provider credentials; default disables provider')
    parser.add_argument('--route-harness',action='store_true',help='Opt-in router-only IR-14 scope if full app import is blocked')
    args=parser.parse_args(argv)
    if args.list:
        for case,description in CASE_NAMES.items():
            print(case,description,('prerequisite: '+','.join(PRECONDITIONS[case])) if case in PRECONDITIONS and PRECONDITIONS[case] else '')
        return 0
    require_project(require_working_db=args.full or args.all or bool(args.case))
    full=args.full or args.all
    quick=args.quick or args.all
    if full:
        old_cases=[path for path in [AUDIT/'evidence'/'baseline']+[AUDIT/'evidence'/case for case in CASE_NAMES] if path.exists()]
        if old_cases:
            raise SystemExit('Existing audit case/baseline folders found: '+', '.join(str(path) for path in old_cases)+'\nArchive your old audit *outside* the project first to prevent old runs being mistaken for current evidence. This launcher never deletes files.')
    if args.case and not (AUDIT/'evidence'/'baseline'/'database_backup.json').exists():
        raise SystemExit('Missing fresh audit baseline/backup; run --full first (after archiving old audit).')
    if args.dry_run:
        stages=(['QUICK (isolated, no live LLM)'] if quick else [])+(['BASELINE inspect','BASELINE backup','BASELINE existing pytest','BASELINE IR evaluation','BASELINE smoke']+list(CASE_NAMES) if full else [])+([args.case] if args.case else [])
        for stage in stages:print(stage)
        return 0
    env=mode_env(args.allow_live_llm)
    print('Project: '+str(ROOT), 'Provider: '+('opted-in to current .env' if args.allow_live_llm else 'disabled'),sep='\n')
    logdir=AUDIT/'evidence'/'retest_suite'/('run-'+utc_stamp())
    logdir.mkdir(parents=True,exist_ok=False)
    results=[]
    py=sys.executable
    if quick:
        # conftest creates a separate temporary SQLite database before app imports.
        results.append(run_step('Quick component tests',[py,'-B','-m','pytest','-q','-p','no:cacheprovider',str(RUNNER/'quick_tests')],logdir,env,240))
    if full:
        collection=RUNNER/'scripts'/'collect_baseline.py'
        for action,minutes in [('inspect',120),('backup',120)]:
            entry=run_step('baseline '+action,[py,'-B',str(collection),action],logdir,env,minutes)
            results.append(entry)
            if entry['exit_code']!=0:
                print('Baseline failed; no original cases executed. Inspect '+str(logdir),flush=True)
                render_report(logdir,results,args.allow_live_llm)
                return 1
        for action,timeout in [('tests',480),('evaluation',480),('smoke',480)]:
            results.append(run_step('baseline '+action,[py,'-B',str(collection),action,'--low-memory'],logdir,env,timeout))
        for case in CASE_NAMES:
            prerequisites=PRECONDITIONS.get(case,[])
            absent=[previous for previous in prerequisites if not list((AUDIT/'evidence'/previous).glob('run-*'))]
            if absent:
                print('[BLOCKED] '+case+' requires '+', '.join(absent),flush=True)
                results.append({'step':case,'command':[],'exit_code':None,'timed_out':False,'seconds':0.0,'blocked_by':absent})
                continue
            command=[py,'-B',str(RUNNER/'scripts'/('run_ir'+case[-2:]+'.py'))]
            if case=='IR-14' and args.route_harness:command.append('--route-harness')
            results.append(run_step(case,command,logdir,env,750))
    if args.case:
        case=args.case
        absent=[previous for previous in PRECONDITIONS.get(case,[]) if not list((AUDIT/'evidence'/previous).glob('run-*'))]
        if absent:raise SystemExit('Missing previous case(s): '+', '.join(absent))
        command=[py,'-B',str(RUNNER/'scripts'/('run_ir'+case[-2:]+'.py'))]
        if case=='IR-14' and args.route_harness:command.append('--route-harness')
        results.append(run_step(case,command,logdir,env,750))
    render_report(logdir,results,args.allow_live_llm)
    return 1 if any(item['exit_code']!=0 for item in results) else 0


if __name__=='__main__':
    sys.exit(main())
