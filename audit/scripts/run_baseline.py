"""Run a baseline action and retain native-library failures and its actual process exit."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from collect_baseline import BASELINE, EVIDENCE, ROOT, clean, save, digest, code_hashes, stamp
parser=argparse.ArgumentParser()
parser.add_argument("action",choices=["tests","evaluation","smoke"])
parser.add_argument("--low-memory",action="store_true")
args=parser.parse_args()
before=digest(ROOT/"knowgap.db")
command=[sys.executable,"-B",str(ROOT/"audit"/"scripts"/"collect_baseline.py"),args.action]
if args.low_memory:
    command.append("--low-memory")
start=time.perf_counter()
timed_out=False
try:
    completed=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",timeout=300,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    code=completed.returncode
    output=completed.stdout+"\n"+completed.stderr
except subprocess.TimeoutExpired as exc:
    timed_out=True
    code=None
    output=(exc.stdout or b"")+(exc.stderr or b"")
    if isinstance(output,bytes):
        output=output.decode("utf-8",errors="replace")
save(args.action+"_process_output.txt",output)
original=json.loads((BASELINE/"environment.json").read_text(encoding="utf-8"))
result={"recorded_at_utc":stamp(),"command":command,"exit_code":code,"timed_out":timed_out,"elapsed_seconds":round(time.perf_counter()-start,3),"thread_limit":1 if args.low_memory else "unchanged","original_database_main_file_unchanged":before==digest(ROOT/"knowgap.db"),"production_sources_unchanged":code_hashes()==original["source_sha256"],"integrity_limit":"Main-file hashes do not cover concurrent changes in a separate SQLite WAL. Helper never opens the original DB for writing."}
save(args.action+"_process_result.json",result)
print(clean(json.dumps(result)))
raise SystemExit(1 if timed_out or code else 0)
