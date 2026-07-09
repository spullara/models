#!/usr/bin/env python3
"""Generate a CSV of (company, model, first_release_date) using git history."""
import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "update_readme.py"

spec = importlib.util.spec_from_file_location("update_readme", SCRIPT_PATH)
update_readme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_readme)


def first_commit_date(filename):
    """Return the date of the first commit that touched filename."""
    result = subprocess.run(
        ['git', 'log', '--all', '--reverse', '--format=%ad', '--date=short', '--', filename],
        capture_output=True, text=True, check=True,
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    return lines[0].strip() if lines else None


rows = []
for filename, provider in update_readme.PROVIDER_MAP.items():
    data = update_readme.get_model_history(filename)
    initial_date = first_commit_date(filename)
    for model, date in data['added'].items():
        # Drop models that were already present in the first commit for this provider.
        if initial_date is not None and date == initial_date:
            continue
        rows.append((provider, model, date))

# Deduplicate keeping earliest date per (company, model)
best = {}
for company, model, date in rows:
    key = (company, model)
    if key not in best or date < best[key]:
        best[key] = date

writer = csv.writer(sys.stdout)
writer.writerow(['company', 'model', 'first_release_date'])
for (company, model), date in sorted(best.items(), key=lambda x: (x[1], x[0][0], x[0][1])):
    writer.writerow([company, model, date])
