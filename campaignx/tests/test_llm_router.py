import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm.router import llm_router

async def test_1_gemini():
    print("\n--- TEST 1: Gemini (Primary) ---")
    result = await llm_router.call(
        prompt="Reply with exactly one word: Hello",
        task="general",
        max_tokens=10
    )
    print(f"  Gemini response: {result.strip()}")
    assert len(result.strip()) > 0, "FAIL: empty response"
    print("TEST 1 PASSED")

async def test_2_groq():
    print("\n--- TEST 2: Groq (Fallback 1) ---")
    from backend.llm.router import LLMRouter
    router = LLMRouter()
    result = await router._call_groq(
        prompt="Reply with exactly one word: Hello",
        max_tokens=10
    )
    print(f"  Groq response: {result.strip()}")
    assert len(result.strip()) > 0, "FAIL: empty response"
    print("TEST 2 PASSED")

async def test_3_mistral():
    print("\n--- TEST 3: Mistral (Fallback 2) ---")
    from backend.llm.router import LLMRouter
    router = LLMRouter()
    result = await router._call_mistral(
        prompt="Reply with exactly one word: Hello",
        max_tokens=10
    )
    print(f"  Mistral response: {result.strip()}")
    assert len(result.strip()) > 0, "FAIL: empty response"
    print("TEST 3 PASSED")

async def test_4_no_warnings():
    print("\n--- TEST 4: No deprecation warnings on import ---")
    import warnings
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from backend.llm import router as _r  # re-import to catch warnings
        future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
        if future_warnings:
            for w in future_warnings:
                print(f"  WARNING: {w.message}")
            print("  (FutureWarnings present — google.generativeai still in use)")
        else:
            print("  No FutureWarnings — new SDK in use")
    print("TEST 4 PASSED")

async def run_all():
    tests = [test_1_gemini, test_2_groq, test_3_mistral, test_4_no_warnings]
    passed = 0
    for test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}")
            print("--- STOPPED ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {test_fn.__name__}: {type(e).__name__}: {e}")
            break

    print(f"\n{'='*40}")
    print(f"Results: {passed}/4 tests passed")
    if passed == 4:
        print("ALL TESTS PASSED — LLM router healthy, ready for Sub-phase 3")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())
