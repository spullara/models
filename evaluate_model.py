#!/usr/bin/env python3
"""
Model evaluation module.
Runs a coding challenge prompt on new models and records results.
"""

import os
import re
import time
import subprocess
import tempfile
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

MODELS_DIR = Path(__file__).parent
EVAL_DIR = MODELS_DIR / "evals"

# The evaluation prompt - a complex algorithmic challenge
EVAL_PROMPT = """Write a Python function with this exact signature:

def solve_grid(grid: list[list[int]]) -> tuple[int, str]:

The function finds the path from top-left to bottom-right of an N×N
grid that maximizes the sum. Rules:
- Valid moves: right (R), down (D), diagonal down-right (X)
- Every 3rd move (3, 6, 9...) MUST be diagonal if possible from current position
- If diagonal is not possible on a required diagonal move, you may use R or D
- Return (max_sum, path_string) e.g., (73, "RRXDDX")

Output ONLY the Python code. No explanations, no markdown, no examples."""

# Test grid for verification
TEST_GRID = [
    [1,  2,  3,  4],
    [5,  6,  7,  8],
    [9,  10, 11, 12],
    [13, 14, 15, 16]
]


def get_chat_endpoint(provider: str) -> dict:
    """Get the chat completions endpoint config for a provider."""
    endpoints = {
        'openai': {
            'url': 'https://api.openai.com/v1/chat/completions',
            'headers': lambda: {
                'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}",
                'Content-Type': 'application/json'
            },
            'format': 'openai'
        },
        'anthropic': {
            'url': 'https://api.anthropic.com/v1/messages',
            'headers': lambda: {
                'x-api-key': os.getenv('ANTHROPIC_API_KEY'),
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            },
            'format': 'anthropic'
        },
        'gemini': {
            'url': lambda model: f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={os.getenv('GEMINI_API_KEY')}",
            'headers': lambda: {'Content-Type': 'application/json'},
            'format': 'gemini'
        },
        'grok': {
            'url': 'https://api.x.ai/v1/chat/completions',
            'headers': lambda: {
                'Authorization': f"Bearer {os.getenv('GROK_API_KEY')}",
                'Content-Type': 'application/json'
            },
            'format': 'openai'
        },
        'mistral': {
            'url': 'https://api.mistral.ai/v1/chat/completions',
            'headers': lambda: {
                'Authorization': f"Bearer {os.getenv('MISTRAL_API_KEY')}",
                'Content-Type': 'application/json'
            },
            'format': 'openai'
        },
        'deepseek': {
            'url': 'https://api.deepseek.com/chat/completions',
            'headers': lambda: {
                'Authorization': f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
                'Content-Type': 'application/json'
            },
            'format': 'openai'
        },
        'kimi': {
            'url': 'https://api.moonshot.ai/v1/chat/completions',
            'headers': lambda: {
                'Authorization': f"Bearer {os.getenv('MOONSHOT_API_KEY')}",
                'Content-Type': 'application/json'
            },
            'format': 'openai'
        },
        'qwen': {
            'url': 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions',
            'headers': lambda: {
                'Authorization': f"Bearer {os.getenv('DASHSCOPE_API_KEY')}",
                'Content-Type': 'application/json'
            },
            'format': 'openai'
        }
    }
    return endpoints.get(provider)


def build_request_body(provider: str, model: str, prompt: str) -> dict:
    """Build the request body for a chat completion."""
    endpoint = get_chat_endpoint(provider)
    if not endpoint:
        return None

    fmt = endpoint['format']

    if fmt == 'openai':
        return {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 16384  # Higher limit for reasoning models
        }
    elif fmt == 'anthropic':
        return {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 16384
        }
    elif fmt == 'gemini':
        return {
            'contents': [{'parts': [{'text': prompt}]}]
        }
    return None


def extract_response_text(provider: str, response_json: dict) -> str:
    """Extract the text response from provider-specific JSON."""
    endpoint = get_chat_endpoint(provider)
    if not endpoint:
        return None

    fmt = endpoint['format']

    try:
        if fmt == 'openai':
            message = response_json['choices'][0]['message']
            content = message.get('content') or ''
            # Some reasoning models (like kimi-k2.5) put the response in reasoning_content
            reasoning_content = message.get('reasoning_content') or ''
            # Return content if non-empty, otherwise try reasoning_content
            return content if content.strip() else reasoning_content
        elif fmt == 'anthropic':
            return response_json['content'][0]['text']
        elif fmt == 'gemini':
            return response_json['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError) as e:
        return None
    return None


def call_model(provider: str, model: str, prompt: str) -> tuple[str, float, str]:
    """
    Call a model with a prompt and return (response_text, elapsed_time, error).
    """
    endpoint = get_chat_endpoint(provider)
    if not endpoint:
        return None, 0, f"Unknown provider: {provider}"

    url = endpoint['url']
    if callable(url):
        url = url(model)

    headers = endpoint['headers']()
    body = build_request_body(provider, model, prompt)

    if not body:
        return None, 0, "Failed to build request body"

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=body, timeout=300)
        elapsed = time.time() - start_time

        if response.status_code != 200:
            return None, elapsed, f"HTTP {response.status_code}: {response.text[:500]}"

        response_json = response.json()
        text = extract_response_text(provider, response_json)

        if not text:
            return None, elapsed, "Failed to extract response text"

        return text, elapsed, None

    except requests.exceptions.Timeout:
        return None, 300, "Request timed out (5 min)"
    except Exception as e:
        return None, 0, str(e)


def extract_code(response: str) -> tuple[str, str]:
    """
    Extract Python code from a model response.
    Returns (code, extraction_method).
    """
    if not response:
        return None, "no_response"

    # Method 1: Try direct parse (response is just code)
    if "def solve_grid" in response:
        # Check if it looks like pure code (no markdown)
        if not response.strip().startswith("```"):
            # Try to compile it
            try:
                compile(response, '<string>', 'exec')
                return response.strip(), "direct"
            except SyntaxError:
                pass

    # Method 2: Extract from ```python blocks
    match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
    if match and "def solve_grid" in match.group(1):
        code = match.group(1).strip()
        try:
            compile(code, '<string>', 'exec')
            return code, "markdown_python"
        except SyntaxError:
            pass

    # Method 3: Extract from ``` blocks (no language)
    match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if match and "def solve_grid" in match.group(1):
        code = match.group(1).strip()
        try:
            compile(code, '<string>', 'exec')
            return code, "markdown_generic"
        except SyntaxError:
            pass

    # Method 4: Find function definition and extract
    match = re.search(r'(def solve_grid\s*\([^)]*\)[^:]*:.*?)(?=\n(?:def |class |if __name__|$)|\Z)',
                      response, re.DOTALL)
    if match:
        code = match.group(1).strip()
        # Add any imports that might be before the function
        imports = re.findall(r'^(?:from .+ import .+|import .+)$', response, re.MULTILINE)
        if imports:
            code = '\n'.join(imports) + '\n\n' + code
        try:
            compile(code, '<string>', 'exec')
            return code, "function_extract"
        except SyntaxError:
            pass

    return None, "extraction_failed"


def validate_path(grid: list[list[int]], path: str) -> tuple[bool, int, str]:
    """
    Validate a path through the grid.
    Returns (is_valid, calculated_sum, error_message).
    """
    n = len(grid)
    row, col = 0, 0
    total = grid[0][0]
    move_count = 0

    for i, move in enumerate(path):
        move_count += 1
        is_third_move = (move_count % 3 == 0)

        # Calculate next position
        if move == 'R':
            new_row, new_col = row, col + 1
        elif move == 'D':
            new_row, new_col = row + 1, col
        elif move == 'X':
            new_row, new_col = row + 1, col + 1
        else:
            return False, total, f"Invalid move character: {move}"

        # Check bounds
        if new_row >= n or new_col >= n:
            return False, total, f"Move {move} at step {i+1} goes out of bounds"

        # Check 3rd move rule
        if is_third_move:
            # Check if diagonal was possible
            diag_possible = (row + 1 < n and col + 1 < n)
            if diag_possible and move != 'X':
                return False, total, f"Move {move_count} must be diagonal (X) but was {move}"

        row, col = new_row, new_col
        total += grid[row][col]

    # Check if we reached the end
    if row != n - 1 or col != n - 1:
        return False, total, f"Path ended at ({row}, {col}) instead of ({n-1}, {n-1})"

    return True, total, None


def execute_code(code: str, grid: list[list[int]], timeout: int = 10) -> tuple[any, str]:
    """
    Execute the extracted code and return (result, error).
    Runs in a subprocess for safety.
    """
    test_script = f'''
import sys
import json

{code}

grid = {grid}
try:
    result = solve_grid(grid)
    print(json.dumps({{"success": True, "result": result}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_file = f.name

    try:
        result = subprocess.run(
            ['python3', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            return None, f"Execution error: {result.stderr[:500]}"

        import json
        try:
            output = json.loads(result.stdout.strip())
            if output.get('success'):
                return output['result'], None
            else:
                return None, output.get('error', 'Unknown error')
        except json.JSONDecodeError:
            return None, f"Invalid output: {result.stdout[:500]}"

    except subprocess.TimeoutExpired:
        return None, f"Execution timed out ({timeout}s)"
    except Exception as e:
        return None, str(e)
    finally:
        os.unlink(temp_file)


def evaluate_model(provider: str, model: str) -> dict:
    """
    Run the full evaluation on a model.
    Returns a dict with all evaluation results.
    """
    results = {
        'provider': provider,
        'model': model,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'prompt': EVAL_PROMPT,
        'response': None,
        'response_time': 0,
        'api_error': None,
        'extraction_method': None,
        'extracted_code': None,
        'syntax_valid': False,
        'execution_result': None,
        'execution_error': None,
        'path_valid': False,
        'path_error': None,
        'returned_sum': None,
        'calculated_sum': None,
        'sum_matches': False,
    }

    # Step 1: Call the model
    print(f"  Calling {provider}/{model}...")
    response, elapsed, error = call_model(provider, model, EVAL_PROMPT)
    results['response_time'] = round(elapsed, 2)

    if error:
        results['api_error'] = error
        return results

    results['response'] = response

    # Step 2: Extract code
    print(f"  Extracting code...")
    code, method = extract_code(response)
    results['extraction_method'] = method

    if not code:
        return results

    results['extracted_code'] = code
    results['syntax_valid'] = True

    # Step 3: Execute code
    print(f"  Executing code...")
    result, exec_error = execute_code(code, TEST_GRID)

    if exec_error:
        results['execution_error'] = exec_error
        return results

    results['execution_result'] = result

    # Step 4: Validate result
    if isinstance(result, (list, tuple)) and len(result) == 2:
        returned_sum, path = result
        results['returned_sum'] = returned_sum

        if isinstance(path, str):
            print(f"  Validating path...")
            is_valid, calc_sum, path_error = validate_path(TEST_GRID, path)
            results['path_valid'] = is_valid
            results['path_error'] = path_error
            results['calculated_sum'] = calc_sum
            results['sum_matches'] = (returned_sum == calc_sum)

    return results


def save_evaluation(results: dict) -> str:
    """Save evaluation results to a file."""
    # Create evals directory if needed
    EVAL_DIR.mkdir(exist_ok=True)

    # Sanitize model name for filename
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', results['model'])
    filename = f"eval-{safe_name}.txt"
    filepath = EVAL_DIR / filename

    # Build output
    lines = [
        f"Model: {results['model']}",
        f"Provider: {results['provider']}",
        f"Evaluated: {results['timestamp']}",
        "",
        "=== TIMING ===",
        f"Response time: {results['response_time']}s",
        "",
        "=== CODE EXTRACTION ===",
        f"Method: {results['extraction_method']}",
        f"Syntax valid: {'YES' if results['syntax_valid'] else 'NO'}",
        "",
        "=== EXECUTION ===",
    ]

    if results['api_error']:
        lines.append(f"API Error: {results['api_error']}")
    elif results['execution_error']:
        lines.append(f"Execution Error: {results['execution_error']}")
    else:
        lines.extend([
            f"Returned sum: {results['returned_sum']}",
            f"Calculated sum: {results['calculated_sum']}",
            f"Sum matches: {'YES' if results['sum_matches'] else 'NO'}",
            f"Path valid: {'YES' if results['path_valid'] else 'NO'}",
        ])
        if results['path_error']:
            lines.append(f"Path error: {results['path_error']}")

    lines.extend([
        "",
        "=== RAW RESPONSE ===",
        results['response'] or "(no response)",
        "",
        "=== EXTRACTED CODE ===",
        results['extracted_code'] or "(no code extracted)",
    ])

    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))

    print(f"  Saved to {filename}")
    return str(filepath)


def run_evaluation(provider: str, model: str) -> dict:
    """Main entry point: evaluate a model and save results."""
    print(f"Evaluating {provider}/{model}...")
    results = evaluate_model(provider, model)
    save_evaluation(results)
    return results


if __name__ == "__main__":
    # Test with a sample model
    import sys
    if len(sys.argv) >= 3:
        provider = sys.argv[1]
        model = sys.argv[2]
        results = run_evaluation(provider, model)
        print(f"\nResults: {results['path_valid']=}, {results['sum_matches']=}")
    else:
        print("Usage: python evaluate_model.py <provider> <model>")
        print("Example: python evaluate_model.py openai gpt-4o")
