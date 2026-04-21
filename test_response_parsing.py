#!/usr/bin/env python3
"""
Test script to verify response parsing for Grok Responses API format.
"""

import sys
import json
from evaluate_model import extract_response_text

def test_response_parsing():
    """Test that response parsing works for Responses API format."""
    print("Testing Responses API response parsing...")
    
    # Sample response from X.AI Responses API (based on OpenAI Responses API format)
    sample_response = {
        "id": "resp_abc123",
        "object": "response",
        "created": 1234567890,
        "model": "grok-4.20-0309-reasoning",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": "def solve_grid(grid):\n    # This is a test response\n    return (100, 'RRXDDX')"
                    }
                ]
            }
        ],
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50
        }
    }
    
    print("\nSample Responses API response:")
    print(json.dumps(sample_response, indent=2))
    
    # Test extraction
    print("\nExtracting response text...")
    extracted_text = extract_response_text('grok', sample_response)
    
    if not extracted_text:
        print("❌ FAIL: Could not extract text from response")
        return False
    
    print(f"\n✓ Extracted text:")
    print(extracted_text)
    
    expected_text = "def solve_grid(grid):\n    # This is a test response\n    return (100, 'RRXDDX')"
    
    if extracted_text != expected_text:
        print(f"\n❌ FAIL: Extracted text doesn't match expected")
        print(f"Expected: {expected_text}")
        print(f"Got: {extracted_text}")
        return False
    
    print("\n✓ Text extraction successful!")
    
    # Test alternative format (with 'text' type instead of 'output_text')
    print("\n" + "="*60)
    print("Testing alternative format (text type)...")
    
    alt_response = {
        "id": "resp_def456",
        "object": "response",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "text",
                        "text": "Alternative format test"
                    }
                ]
            }
        ]
    }
    
    extracted_alt = extract_response_text('grok', alt_response)
    
    if not extracted_alt:
        print("❌ FAIL: Could not extract text from alternative format")
        return False
    
    if extracted_alt != "Alternative format test":
        print(f"❌ FAIL: Alternative format extraction failed")
        print(f"Expected: 'Alternative format test'")
        print(f"Got: '{extracted_alt}'")
        return False
    
    print("✓ Alternative format extraction successful!")
    
    print("\n" + "="*60)
    print("✅ All response parsing tests passed!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    success = test_response_parsing()
    sys.exit(0 if success else 1)
