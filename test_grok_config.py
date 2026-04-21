#!/usr/bin/env python3
"""
Test script to verify Grok API configuration for Responses API.
"""

import sys
import json
from evaluate_model import get_chat_endpoint, build_request_body

def test_grok_config():
    """Test that Grok is configured to use the Responses API."""
    print("Testing Grok API configuration...")
    
    # Get the endpoint config
    config = get_chat_endpoint('grok')
    
    if not config:
        print("❌ FAIL: Could not get Grok endpoint configuration")
        return False
    
    print(f"\n✓ Endpoint URL: {config['url']}")
    print(f"✓ Format: {config['format']}")
    
    # Verify it's using the Responses API
    expected_url = 'https://api.x.ai/v1/responses'
    expected_format = 'openai_responses'
    
    if config['url'] != expected_url:
        print(f"❌ FAIL: Expected URL '{expected_url}', got '{config['url']}'")
        return False
    
    if config['format'] != expected_format:
        print(f"❌ FAIL: Expected format '{expected_format}', got '{config['format']}'")
        return False
    
    print("\n✓ Configuration is correct!")
    
    # Test request body format
    print("\nTesting request body format...")
    body = build_request_body('grok', 'grok-4.20-0309-reasoning', 'Test prompt')
    
    if not body:
        print("❌ FAIL: Could not build request body")
        return False
    
    print(f"\nRequest body structure:")
    print(json.dumps(body, indent=2))
    
    # Verify the structure matches openai_responses format
    if 'model' not in body:
        print("❌ FAIL: Request body missing 'model' field")
        return False
    
    if 'input' not in body:
        print("❌ FAIL: Request body missing 'input' field (Responses API format)")
        return False
    
    if not isinstance(body['input'], list):
        print("❌ FAIL: 'input' should be a list")
        return False
    
    if len(body['input']) == 0:
        print("❌ FAIL: 'input' list is empty")
        return False
    
    # Check first input item
    first_input = body['input'][0]
    if 'role' not in first_input or 'content' not in first_input:
        print("❌ FAIL: Input messages should have 'role' and 'content' fields")
        return False
    
    print("\n✓ Request body format is correct for Responses API!")
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)
    print("\nGrok is now configured to use:")
    print(f"  • Endpoint: {expected_url}")
    print(f"  • Format: {expected_format}")
    print(f"  • Request structure: input[] instead of messages[]")
    
    return True

if __name__ == "__main__":
    success = test_grok_config()
    sys.exit(0 if success else 1)
