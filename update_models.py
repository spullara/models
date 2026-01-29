#!/usr/bin/env python3
"""
Script to fetch model lists from various AI providers and update txt files.
Uses .env file for API keys instead of hardcoding them.
When new models are detected, runs an evaluation prompt on them.
"""

import os
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from evaluate_model import run_evaluation

# Load environment variables from .env file
load_dotenv()

# Get the models directory (current directory)
MODELS_DIR = Path(__file__).parent

# Provider configurations
PROVIDERS = {
    'openai': {
        'url': 'https://api.openai.com/v1/models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        'json_path': ['data', 'id'],
        'output_file': 'openai.txt'
    },
    'anthropic': {
        'url': 'https://api.anthropic.com/v1/models',
        'headers': lambda: {
            'x-api-key': os.getenv('ANTHROPIC_API_KEY'),
            'anthropic-version': '2023-06-01'
        },
        'json_path': ['data', 'id'],
        'output_file': 'anthropic.txt'
    },
    'gemini': {
        'url': f"https://generativelanguage.googleapis.com/v1beta/models?key={os.getenv('GEMINI_API_KEY')}",
        'headers': lambda: {},
        'json_path': ['models', 'name'],
        'output_file': 'gemini.txt'
    },
    'grok': {
        'urls': [
            'https://api.x.ai/v1/language-models',
            'https://api.x.ai/v1/embedding-models',
            'https://api.x.ai/v1/image-generation-models',
            'https://api.x.ai/v1/video-generation-models'
        ],
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('GROK_API_KEY')}"},
        'json_path': ['models', 'id'],
        'output_file': 'grok.txt'
    },
    'mistral': {
        'url': 'https://api.mistral.ai/v1/models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('MISTRAL_API_KEY')}"},
        'json_path': ['data', 'id'],
        'output_file': 'mistral.txt'
    },
    'deepseek': {
        'url': 'https://api.deepseek.com/models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('DEEPSEEK_API_KEY')}"},
        'json_path': ['data', 'id'],
        'output_file': 'deepseek.txt'
    },
    'kimi': {
        'url': 'https://api.moonshot.ai/v1/models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('MOONSHOT_API_KEY')}"},
        'json_path': ['data', 'id'],
        'output_file': 'kimi.txt'
    },
    'qwen': {
        'url': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
        'json_path': ['data', 'id'],
        'output_file': 'qwen.txt'
    }
}

def is_fine_tuned_model(model_name):
    """Check if a model is a fine-tuned model."""
    if not model_name:
        return False
    # Check if starts with "ft:"
    if model_name.startswith('ft:'):
        return True
    # Check if contains ":ft-" pattern
    if ':ft-' in model_name:
        return True
    return False

def extract_from_json(data, path):
    """Extract values from JSON using a path like ['data', 'id']."""
    if len(path) == 1:
        # Base case: extract the field from each item
        if isinstance(data, list):
            return [item.get(path[0]) for item in data if path[0] in item]
        return []

    # Recursive case: navigate deeper
    if isinstance(data, dict) and path[0] in data:
        return extract_from_json(data[path[0]], path[1:])
    return []

def fetch_models(provider_name, config):
    """Fetch models for a given provider."""
    print(f"Fetching models for {provider_name}...")

    try:
        headers = config['headers']()

        # Support both single 'url' and multiple 'urls'
        urls = config.get('urls', [config['url']] if 'url' in config else [])
        all_models = []

        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                models = extract_from_json(data, config['json_path'])
                if models:
                    all_models.extend(models)
            except requests.exceptions.RequestException as e:
                print(f"  Warning: Error fetching from {url}: {e}")
                continue

        if not all_models:
            print(f"  Warning: No models found for {provider_name}")
            return []

        # Filter out fine-tuned models
        original_count = len(all_models)
        all_models = [m for m in all_models if not is_fine_tuned_model(m)]
        filtered_count = original_count - len(all_models)

        if filtered_count > 0:
            print(f"  Filtered out {filtered_count} fine-tuned models")

        # Sort models
        all_models = sorted(set(all_models))  # Use set to remove any duplicates
        print(f"  Found {len(all_models)} models")
        return all_models

    except Exception as e:
        print(f"  Unexpected error for {provider_name}: {e}")
        return []

def read_existing_models(output_file):
    """Read existing models from a file."""
    file_path = MODELS_DIR / output_file
    if not file_path.exists():
        return set()
    with open(file_path, 'r') as f:
        return set(line.strip() for line in f if line.strip())


def write_models_file(output_file, models):
    """Write models to a file."""
    file_path = MODELS_DIR / output_file
    with open(file_path, 'w') as f:
        for model in models:
            f.write(f"{model}\n")
    print(f"  Written to {output_file}")

def git_commit_if_changed(file_path):
    """Add and commit file if it has content."""
    try:
        # Check if file has content
        if os.path.getsize(file_path) > 0:
            subprocess.run(['git', 'add', file_path], check=True, cwd=MODELS_DIR)
            subprocess.run(['git', 'commit', '-am', 'update'], check=False, cwd=MODELS_DIR)
    except Exception as e:
        print(f"  Git error: {e}")

def evaluate_new_models(provider_name, new_models):
    """Evaluate newly detected models."""
    if not new_models:
        return

    print(f"\n  Found {len(new_models)} new model(s) for {provider_name}:")
    for model in sorted(new_models):
        print(f"    - {model}")

    for model in sorted(new_models):
        try:
            run_evaluation(provider_name, model)
        except Exception as e:
            print(f"    Error evaluating {model}: {e}")


def main():
    """Main function to update all provider model lists."""
    os.chdir(MODELS_DIR)

    # Pull latest changes
    print("Pulling latest changes...")
    try:
        subprocess.run(['git', 'pull'], check=True, cwd=MODELS_DIR)
    except Exception as e:
        print(f"Git pull error: {e}")

    # Track all new models for evaluation
    all_new_models = {}

    # Process each provider
    for provider_name, config in PROVIDERS.items():
        # Read existing models before fetching
        existing_models = read_existing_models(config['output_file'])

        # Fetch current models
        models = fetch_models(provider_name, config)
        if models:
            # Detect new models
            new_models = set(models) - existing_models
            if new_models:
                all_new_models[provider_name] = new_models

            write_models_file(config['output_file'], models)
            git_commit_if_changed(MODELS_DIR / config['output_file'])

    # Evaluate new models
    if all_new_models:
        print("\n" + "=" * 50)
        print("EVALUATING NEW MODELS")
        print("=" * 50)
        for provider_name, new_models in all_new_models.items():
            evaluate_new_models(provider_name, new_models)

        # Commit evaluation results
        print("\nCommitting evaluation results...")
        try:
            evals_dir = MODELS_DIR / "evals"
            if evals_dir.exists():
                subprocess.run(['git', 'add', 'evals/'], check=True, cwd=MODELS_DIR)
                subprocess.run(
                    ['git', 'commit', '-m', 'Add model evaluation results'],
                    check=False, cwd=MODELS_DIR
                )
        except Exception as e:
            print(f"  Git error committing evals: {e}")

    # Reset any uncommitted changes
    print("\nResetting uncommitted changes...")
    try:
        subprocess.run(['git', 'reset', '--hard'], check=True, cwd=MODELS_DIR)
    except Exception as e:
        print(f"Git reset error: {e}")

    # Push changes
    print("Pushing changes...")
    try:
        subprocess.run(['git', 'push'], check=True, cwd=MODELS_DIR)
    except Exception as e:
        print(f"Git push error: {e}")

    print("\nDone!")

if __name__ == "__main__":
    main()

