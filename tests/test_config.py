"""Quick test to verify configuration works"""

from academe.config import settings, get_llm

print("=" * 60)
print("Testing Academe Configuration")
print("=" * 60)

# Test 1: Settings loaded
print(f"\n✅ Settings loaded successfully")
print(f"   Provider: {settings.llm_provider}")
print(f"   Log Level: {settings.log_level}")
print(f"   API Key present: {settings.google_api_key is not None}")

# Test 2: LLM creation
print(f"\n✅ Creating LLM instance...")
llm = get_llm()
print(f"   LLM Type: {type(llm).__name__}")
print(f"   Model: gemini-1.5-flash")

# Test 3: Simple LLM call
print(f"\n✅ Testing LLM with simple query...")
response = llm.invoke("Say 'Configuration test successful!' and nothing else.")
print(f"   Response: {response.content}")

print("\n" + "=" * 60)
print("All configuration tests passed! 🎉")
print("=" * 60)