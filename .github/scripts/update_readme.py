#!/usr/bin/env python3
"""
Script to update README.md with model changes from txt files.
This script is meant to be run by GitHub Actions when txt files change.
"""

import os
import subprocess
import re
import json
from datetime import datetime, timedelta

# Map of file names to provider names
PROVIDER_MAP = {
    'openai.txt': 'OpenAI',
    'anthropic.txt': 'Anthropic',
    'gemini.txt': 'Gemini'
}

def get_changed_files():
    """Get list of changed txt files in the last commit."""
    # For testing outside of GitHub Actions
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        return [f for f in PROVIDER_MAP.keys() if os.path.exists(f)]

    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
        capture_output=True, text=True, check=True
    )
    changed_files = result.stdout.strip().split('\n')
    return [f for f in changed_files if f.endswith('.txt') and f in PROVIDER_MAP]

def get_file_changes(file_path, since_date=None):
    """Get added and removed lines from a file.

    Args:
        file_path: Path to the file to check for changes
        since_date: If provided, get changes since this date (ISO format YYYY-MM-DD)
                   If None, only get changes in the last commit
    """
    # For testing outside of GitHub Actions
    if os.environ.get('GITHUB_ACTIONS') != 'true' and since_date is None:
        # For testing, we'll simulate changes by reading the current file
        with open(file_path, 'r') as f:
            current_models = [line.strip() for line in f if line.strip()]

        # For testing purposes, we'll consider the last model as newly added
        if current_models:
            return [current_models[-1]], []
        return [], []

    # If we need to get changes since a specific date
    if since_date:
        try:
            # Check if the file exists in git history
            file_exists_cmd = ['git', 'ls-files', '--error-unmatch', file_path]
            subprocess.run(file_exists_cmd, capture_output=True, check=True)

            # Get the commit hash from the specified date
            date_cmd = ['git', 'log', '--since', since_date, '--format=%H', '--', file_path]
            date_result = subprocess.run(date_cmd, capture_output=True, text=True, check=True)
            commit_hashes = date_result.stdout.strip().split('\n')

            # If no commits since that date, try to get the current content
            if not commit_hashes or not commit_hashes[0]:
                # If the file exists but has no commits in the time range,
                # consider all current content as added
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        current_models = [line.strip() for line in f if line.strip()]
                    return current_models, []
                return [], []

            # Get the oldest commit since the specified date
            oldest_commit = commit_hashes[-1] if commit_hashes else 'HEAD'

            # Try to get the commit before the oldest one to use as a reference
            try:
                ref_cmd = ['git', 'rev-parse', f'{oldest_commit}^']
                ref_result = subprocess.run(ref_cmd, capture_output=True, text=True, check=True)
                reference_commit = ref_result.stdout.strip()

                # Get changes between the reference commit and HEAD
                diff_cmd = ['git', 'diff', reference_commit, 'HEAD', '--', file_path]
            except subprocess.CalledProcessError:
                # If there's no parent commit (e.g., first commit), consider all content as added
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        current_models = [line.strip() for line in f if line.strip()]
                    return current_models, []
                return [], []
        except subprocess.CalledProcessError:
            # File doesn't exist in git history, but might exist on disk
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    current_models = [line.strip() for line in f if line.strip()]
                return current_models, []
            return [], []
    else:
        # Just get changes in the last commit
        try:
            # Check if we have at least one commit
            subprocess.run(['git', 'rev-parse', 'HEAD~1'], capture_output=True, check=True)
            diff_cmd = ['git', 'diff', 'HEAD~1', 'HEAD', '--', file_path]
        except subprocess.CalledProcessError:
            # If there's only one commit or no commits, consider all content as added
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    current_models = [line.strip() for line in f if line.strip()]
                return current_models, []
            return [], []

    try:
        result = subprocess.run(diff_cmd, capture_output=True, text=True, check=True)

        added_models = []
        removed_models = []

        for line in result.stdout.split('\n'):
            if line.startswith('+') and not line.startswith('++'):
                model = line[1:].strip()
                if model:  # Skip empty lines
                    added_models.append(model)
            elif line.startswith('-') and not line.startswith('--'):
                model = line[1:].strip()
                if model:  # Skip empty lines
                    removed_models.append(model)

        return added_models, removed_models
    except subprocess.CalledProcessError:
        # If git diff fails, return empty lists
        return [], []

def update_readme(changes):
    """Update README.md with model changes."""
    with open('README.md', 'r') as f:
        content = f.read()

    # Extract the first two lines (header)
    lines = content.split('\n')
    header = lines[:2] if len(lines) >= 2 else lines

    # Create new content
    new_content = header[0] + '\n' + header[1] + '\n\n'
    new_content += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # Add changes section
    new_content += "## Model Changes (Last 60 Days)\n\n"

    # Get all providers, including those without changes
    all_providers = set(PROVIDER_MAP.values())
    providers_with_changes = set(changes.keys())

    # First show providers with changes
    for provider, provider_changes in changes.items():
        if provider_changes['added'] or provider_changes['removed']:
            new_content += f"### {provider}\n\n"

            for model in provider_changes['added']:
                new_content += f"+ {model}\n"

            for model in provider_changes['removed']:
                new_content += f"- {model}\n"

            new_content += "\n"

    # Then show providers without changes
    for provider in sorted(all_providers - providers_with_changes):
        new_content += f"### {provider}\n\n"
        new_content += "No changes\n\n"

    # Write updated content back to README
    with open('README.md', 'w') as f:
        f.write(new_content)

def main():
    # Get the date 60 days ago in ISO format (YYYY-MM-DD)
    sixty_days_ago = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')

    # Always check all provider files for the last 60 days of changes
    all_files = [f for f in PROVIDER_MAP.keys() if os.path.exists(f)]

    changes = {}

    for file_path in all_files:
        provider = PROVIDER_MAP.get(file_path)
        if not provider:
            continue

        # Get changes from the last 60 days
        added, removed = get_file_changes(file_path, since_date=sixty_days_ago)

        if added or removed:
            changes[provider] = {
                'added': added,
                'removed': removed
            }

    if changes:
        update_readme(changes)
        print(f"README.md updated with changes from {', '.join(changes.keys())}")
    else:
        print("No model changes detected in the last 30 days.")

if __name__ == "__main__":
    main()
