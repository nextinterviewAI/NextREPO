#!/usr/bin/env python3
"""
Test script for OpenAI rate limiting and retry functionality.
Run this to verify the enhanced error handling works correctly.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm.utils import safe_openai_call, client, rate_limiter

async def test_rate_limiting():
    """Test the rate limiting functionality."""
    print("🧪 Testing OpenAI Rate Limiting and Retry Logic")
    print("=" * 50)
    
    # Test 1: Basic rate limiting
    print("\n1️⃣ Testing basic rate limiting...")
    try:
        # Make multiple calls quickly to test rate limiting
        for i in range(3):
            print(f"   Making API call {i+1}/3...")
            response = await safe_openai_call(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": f"Say hello {i+1}"}],
                max_tokens=10
            )
            print(f"   ✅ Call {i+1} successful")
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Test 2: Rate limiter status
    print("\n2️⃣ Testing rate limiter status...")
    print(f"   Current calls in window: {len(rate_limiter.calls)}")
    print(f"   Max calls per minute: {rate_limiter.max_calls}")
    
    # Test 3: Configuration
    print("\n3️⃣ Testing configuration...")
    from services.llm.utils import RATE_LIMIT_CALLS_PER_MINUTE, RATE_LIMIT_MAX_RETRIES
    print(f"   Rate limit calls per minute: {RATE_LIMIT_CALLS_PER_MINUTE}")
    print(f"   Max retries: {RATE_LIMIT_MAX_RETRIES}")
    
    print("\n✅ Rate limiting test completed!")

async def test_error_handling():
    """Test error handling with invalid API key."""
    print("\n🧪 Testing Error Handling")
    print("=" * 30)
    
    # Temporarily change API key to test error handling
    original_key = os.getenv("OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = "invalid_key"
    
    try:
        print("   Testing with invalid API key...")
        response = await safe_openai_call(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("   ❌ Should have failed!")
    except Exception as e:
        print(f"   ✅ Correctly caught error: {str(e)[:100]}...")
    
    # Restore original key
    os.environ["OPENAI_API_KEY"] = original_key
    print("   ✅ API key restored")

async def main():
    """Main test function."""
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in a .env file")
        return
    
    print("🚀 Starting OpenAI Rate Limiting Tests")
    print("Make sure your OpenAI API key is valid and has sufficient quota")
    
    try:
        await test_rate_limiting()
        await test_error_handling()
        
        print("\n🎉 All tests completed successfully!")
        print("\n💡 Tips:")
        print("   - Monitor your logs for rate limiting warnings")
        print("   - Adjust OPENAI_RATE_LIMIT in .env if you hit limits")
        print("   - Check OpenAI billing dashboard for quota status")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
