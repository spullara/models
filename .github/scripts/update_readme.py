#!/usr/bin/env python3
"""
Script to update README.md with current and deleted models from txt files.
This script is meant to be run by GitHub Actions when txt files change.
"""

import os
import subprocess
from datetime import datetime

# Map of file names to provider names
PROVIDER_MAP = {
    'openai.txt': 'OpenAI',
    'anthropic.txt': 'Anthropic',
    'gemini.txt': 'Gemini',
    'grok.txt': 'Grok',
    'mistral.txt': 'Mistral'
}

def get_current_models(file_path):
    """Get current models from a file."""
    if not os.path.exists(file_path):
        return set()

    with open(file_path, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def get_model_history(file_path):
    """Get the complete history of models (added and deleted) with dates.

    Returns:
        dict: {
            'current': set of current models,
            'added': {model: date_added},
            'deleted': {model: date_deleted}
        }
    """
    current_models = get_current_models(file_path)

    # Track when each model was first added and last deleted
    model_added = {}
    model_deleted = {}

    try:
        # Get all commits that modified this file, in reverse chronological order
        result = subprocess.run(
            ['git', 'log', '--all', '--format=%H|%ad', '--date=short', '--', file_path],
            capture_output=True, text=True, check=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if line and '|' in line:
                commit_hash, date = line.split('|', 1)
                commits.append((commit_hash.strip(), date.strip()))

        if not commits:
            # No history, all current models were just added
            for model in current_models:
                model_added[model] = datetime.now().strftime('%Y-%m-%d')
            return {
                'current': current_models,
                'added': model_added,
                'deleted': model_deleted
            }

        # Process commits from oldest to newest to track additions and deletions
        commits.reverse()

        previous_models = set()
        for commit_hash, date in commits:
            # Get file content at this commit
            try:
                content_result = subprocess.run(
                    ['git', 'show', f'{commit_hash}:{file_path}'],
                    capture_output=True, text=True, check=True
                )
                commit_models = set(line.strip() for line in content_result.stdout.split('\n') if line.strip())
            except subprocess.CalledProcessError:
                commit_models = set()

            # Find models added in this commit
            added_in_commit = commit_models - previous_models
            for model in added_in_commit:
                if model not in model_added:
                    model_added[model] = date

            # Find models removed in this commit
            removed_in_commit = previous_models - commit_models
            for model in removed_in_commit:
                model_deleted[model] = date

            previous_models = commit_models

        # Any model that was deleted but then re-added should not be in deleted list
        for model in current_models:
            if model in model_deleted:
                del model_deleted[model]

    except subprocess.CalledProcessError:
        # If git commands fail, just use current models
        for model in current_models:
            model_added[model] = datetime.now().strftime('%Y-%m-%d')

    return {
        'current': current_models,
        'added': model_added,
        'deleted': model_deleted
    }

def update_readme(all_provider_data):
    """Update README.md with current and deleted models.

    Args:
        all_provider_data: dict mapping provider name to model history data
    """
    with open('README.md', 'r') as f:
        content = f.read()

    # Extract the first two lines (header)
    lines = content.split('\n')
    header = lines[:2] if len(lines) >= 2 else lines

    # Create new content
    new_content = header[0] + '\n' + header[1] + '\n\n'
    new_content += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    # Add summary of models per provider
    new_content += "## Summary\n\n"
    new_content += "Model counts shown as: **Available/Deleted**\n\n"
    for provider in PROVIDER_MAP.values():
        if provider in all_provider_data:
            data = all_provider_data[provider]
            current_count = len(data['current'])
            deleted_count = len(data['deleted'])
            new_content += f"**{provider}**: {current_count}/{deleted_count}\n\n"
    new_content += "\n"

    # Process each provider in the order they appear in PROVIDER_MAP
    for provider in PROVIDER_MAP.values():
        if provider not in all_provider_data:
            continue

        data = all_provider_data[provider]
        current_models = data['current']
        added_dates = data['added']
        deleted_dates = data['deleted']

        new_content += f"## {provider}\n\n"

        # Current models section - sorted by most recently added
        if current_models:
            new_content += "### Current Models\n\n"
            # Sort by date added (most recent first), then by name
            sorted_current = sorted(
                current_models,
                key=lambda m: (added_dates.get(m, '0000-00-00'), m),
                reverse=True
            )
            for model in sorted_current:
                date_str = added_dates.get(model, 'unknown')
                new_content += f"- {model} (added: {date_str})\n"
            new_content += "\n"

        # Deleted models section - sorted by most recently deleted
        if deleted_dates:
            new_content += "### Deleted Models\n\n"
            # Sort by date deleted (most recent first), then by name
            sorted_deleted = sorted(
                deleted_dates.items(),
                key=lambda x: (x[1], x[0]),
                reverse=True
            )
            for model, date in sorted_deleted:
                new_content += f"- {model} (deleted: {date})\n"
            new_content += "\n"

    # Write updated content back to README
    with open('README.md', 'w') as f:
        f.write(new_content)

def main():
    # Check all provider files
    all_files = [f for f in PROVIDER_MAP.keys() if os.path.exists(f)]

    all_provider_data = {}

    for file_path in all_files:
        provider = PROVIDER_MAP.get(file_path)
        if not provider:
            continue

        # Get complete model history
        history = get_model_history(file_path)
        all_provider_data[provider] = history

    if all_provider_data:
        update_readme(all_provider_data)
        print(f"README.md updated with model data from {', '.join(all_provider_data.keys())}")
    else:
        print("No provider data found.")

if __name__ == "__main__":
    main()
