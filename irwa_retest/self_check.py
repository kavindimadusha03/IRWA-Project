"""Standard-library-only static test of the portable IRWA retest kit, no project imports."""
from __future__ import annotations
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
EXPECTED = ['run_all.py','quick_tests/conftest.py','quick_tests/test_ir_01_to_15.py',
            'scripts/collect_baseline.py','scripts/retest_paths.py','scripts/run_baseline.py'] + [
            f'scripts/run_ir{number:02d}.py' for number in range(1,16)]
errors = []
for name in EXPECTED:
    path = ROOT / name
    if not path.is_file():
        errors.append(f'Missing: {name}')
        continue
    try:
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    except (OSError, SyntaxError) as error:
        errors.append(f'Syntax/read error {name}: {error}')
for filename in ('.env','knowgap.db'):
    if (ROOT / filename).exists():
        errors.append(f'Private or forbidden file in kit: {filename}')
for old_file in ROOT.rglob('*'):
    if old_file.is_file() and old_file.suffix in ('.db','.sqlite','.sqlite3','.pem','.key'):
        errors.append(f'Unexpected database/key material in kit: {old_file.relative_to(ROOT)}')
if errors:
    print('Kit self-check FAILED:')
    for error in errors:
        print('  -',error)
    sys.exit(1)
print(f'Kit self-check passed: {len(EXPECTED)} Python files present and parseable; no database or .env inside kit.')
if (PROJECT / 'app' / 'main.py').exists() and (PROJECT / 'requirements.txt').exists():
    print('Kit location: project root detected.')
else:
    print('This folder is not yet beside app/main.py and requirements.txt. Extract into your project root.')
