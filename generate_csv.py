#!/usr/bin/env python3
import subprocess
import csv
from collections import defaultdict

# Get git log with date and file changes
result = subprocess.run(
    ['git', 'log', '--all', '--name-only', '--pretty=format:%ad|%s', '--date=short'],
    capture_output=True,
    text=True,
    cwd='/Users/sam/Projects/models'
)

# Parse the output
lines = result.stdout.strip().split('\n')
date_company_map = defaultdict(set)

current_date = None
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Check if this is a date line (contains |)
    if '|' in line:
        parts = line.split('|')
        current_date = parts[0].strip()
    else:
        # This is a file name
        if current_date and line.endswith('.txt'):
            # Extract company name from filename
            company = line.replace('.txt', '')
            if company in ['anthropic', 'gemini', 'grok', 'openai']:
                date_company_map[current_date].add(company)

# Create list of (date, company) tuples and sort by date
entries = []
for date, companies in date_company_map.items():
    for company in sorted(companies):  # Sort companies alphabetically for consistency
        entries.append((date, company))

# Sort by date (descending - most recent first)
entries.sort(reverse=True)

# Write to CSV
with open('model_commits.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['date', 'model_company'])
    for date, company in entries:
        writer.writerow([date, company])

print(f"Created model_commits.csv with {len(entries)} entries")

