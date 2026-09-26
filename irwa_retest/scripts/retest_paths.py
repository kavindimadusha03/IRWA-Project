"""Locate evidence from THIS retest instead of date-pinned historical runs."""
from pathlib import Path


def latest_run(root: Path, case: str) -> Path:
    base = root / 'audit' / 'evidence' / case
    runs = sorted((p for p in base.glob('run-*') if p.is_dir()), key=lambda p: p.name)
    if not runs:
        raise FileNotFoundError(
            f'{case} has no current run under {base}. Run earlier prerequisites first; do not copy old results.'
        )
    return runs[-1]
