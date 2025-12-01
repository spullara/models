#!/usr/bin/env python3
"""
Script to fetch model lists from various AI providers and update txt files.
Uses .env file for API keys instead of hardcoding them.
"""

import os
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

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
        'url': 'https://api.x.ai/v1/language-models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('GROK_API_KEY')}"},
        'json_path': ['models', 'id'],
        'output_file': 'grok.txt'
    },
    'mistral': {
        'url': 'https://api.mistral.ai/v1/models',
        'headers': lambda: {'Authorization': f"Bearer {os.getenv('MISTRAL_API_KEY')}"},
        'json_path': ['data', 'id'],
        'output_file': 'mistral.txt'
    }
}

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
        response = requests.get(config['url'], headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        models = extract_from_json(data, config['json_path'])
        
        if not models:
            print(f"  Warning: No models found for {provider_name}")
            return []
        
        # Sort models
        models = sorted(models)
        print(f"  Found {len(models)} models")
        return models
        
    except requests.exceptions.RequestException as e:
        print(f"  Error fetching {provider_name}: {e}")
        return []
    except Exception as e:
        print(f"  Unexpected error for {provider_name}: {e}")
        return []

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

def main():
    """Main function to update all provider model lists."""
    os.chdir(MODELS_DIR)
    
    # Pull latest changes
    print("Pulling latest changes...")
    try:
        subprocess.run(['git', 'pull'], check=True, cwd=MODELS_DIR)
    except Exception as e:
        print(f"Git pull error: {e}")
    
    # Process each provider
    for provider_name, config in PROVIDERS.items():
        models = fetch_models(provider_name, config)
        if models:
            write_models_file(config['output_file'], models)
            git_commit_if_changed(MODELS_DIR / config['output_file'])
    
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

