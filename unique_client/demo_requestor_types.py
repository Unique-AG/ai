#!/usr/bin/env python3
"""Demo script showing how to use all RequestorTypes."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import generated_routes.public.messages as messages_api
from generated_routes.endpoint_requestor import RequestContext

# Set up request context
request_context = RequestContext(
    base_url="https://api.example.com",
    headers={
        "Authorization": "Bearer your-token-here",
        "Content-Type": "application/json",
    },
)


def demo_requestor_types():
    """Demo different RequestorTypes available for each operation."""

    print("🚀 Available RequestorTypes for Messages API:")
    print()

    # 1. Standard requests library (always available)
    print("📡 1. Standard Requests (using requests library):")
    print("   messages_api.FindAll.request(context=request_context)")
    print("   messages_api.Create.request(context=request_context, **params)")
    print()

    # 2. Fake requestor (for testing - always available)
    print("🧪 2. Fake Requestor (for testing/mocking):")
    print("   messages_api.FindAllFake.request(context=request_context)")
    print("   messages_api.CreateFake.request(context=request_context, **params)")
    print("   # Returns mock data: {'id': 'fake_response', 'status': 'success'}")
    print()

    # 3. HTTPX requestor (requires httpx package)
    print("⚡ 3. HTTPX Requestor (requires: pip install httpx):")
    print("   messages_api.FindAllHttpx.request(context=request_context)")
    print("   messages_api.CreateHttpx.request(context=request_context, **params)")
    print("   # Supports both sync and async operations")
    print()

    # 4. AIOHTTP requestor (requires aiohttp package)
    print("🌊 4. AIOHTTP Requestor (requires: pip install aiohttp):")
    print("   await messages_api.FindAllAiohttp.request_async(context=request_context)")
    print(
        "   await messages_api.CreateAiohttp.request_async(context=request_context, **params)"
    )
    print("   # Async-only operations")
    print()

    # Test the fake requestor (should work without network)
    print("🧪 Testing Fake Requestor:")
    try:
        fake_requestor = messages_api.FindAllFake()  # Call the factory function
        fake_result = fake_requestor.request(context=request_context)
        print(f"   ✅ Fake response: {fake_result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    print("🧪 Testing Fake Requestor (alternative syntax):")
    try:
        # Direct factory function call
        fake_requestor = messages_api.get_FindAll_fake()
        fake_result = fake_requestor.request(context=request_context)
        print(f"   ✅ Factory function response: {fake_result}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    demo_requestor_types()
