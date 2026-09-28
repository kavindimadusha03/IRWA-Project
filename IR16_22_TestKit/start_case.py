from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil

kit = Path(__file__).resolve().parent
root = kit.parent

parser = argparse.ArgumentParser()
parser.add_argument(
    "--case",
    required=True,
    choices=[f"IR-{n:02d}" for n in range(16, 23)]
)
args = parser.parse_args()

if not (root / "app" / "main.py").is_file():
    raise SystemExit(
        "Place IR16_22_TestKit inside your IRWA-Project folder."
    )

stamp = datetime.now(timezone.utc).strftime(
    "%Y%m%dT%H%M%S%fZ"
)
folder = (
    root / "audit" / "evidence" /
    args.case / ("run-" + stamp)
)
folder.mkdir(parents=True, exist_ok=False)

shutil.copy2(
    kit / "cases" / (args.case + ".md"),
    folder / "expected_result.md"
)
shutil.copy2(
    kit / "fixtures" / (args.case + ".json"),
    folder / "planned_input.json"
)

files = [
    "app/main.py",
    "app/config.py",
    "app/models.py",
    "app/agents/retrieval_agent.py",
    "app/agents/solution_agent.py"
]
source_hashes = {}
for name in files:
    path = root / name
    if path.is_file():
        source_hashes[name] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

(folder / "preconditions.json").write_text(
    json.dumps({
        "case": args.case,
        "recorded_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "NOT EXECUTED",
        "source_sha256": source_hashes,
        "purpose": "Read-only baseline before manual or separately implemented testing."
    }, indent=2),
    encoding="utf-8"
)

(folder / "actual_result.md").write_text(
    "# Actual result\n\nNOT EXECUTED\n\n"
    "## HTTP / retrieval evidence\n\n"
    "## Observations\n\n"
    "## Outcome and limitations\n\n",
    encoding="utf-8"
)

print("Evidence folder prepared:", folder)
print(
    "IMPORTANT: Preparation only. No test request was "
    "sent and no PASS/FAIL result was assigned."
)
