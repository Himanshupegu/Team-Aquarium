import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.brief_parser import parse_brief

BRIEF = (
    "Run email campaign for launching XDeposit, a flagship term deposit product "
    "from SuperBFSI, that gives 1 percentage point higher returns than its competitors. "
    "Announce an additional 0.25 percentage point higher returns for female senior citizens. "
    "Optimise for open rate and click rate. Don't skip emails to customers marked 'inactive'. "
    "Include the call to action: https://superbfsi.com/xdeposit/explore/."
)

REQUIRED_KEYS = [
    "product_name", "key_message", "special_offers", "optimization_goal",
    "include_inactive", "cta_url", "tone", "campaign_type", "target_audience_notes"
]

async def test_1_returns_dict():
    print("\n--- TEST 1: Returns a dict with all required keys ---")
    result = await parse_brief(BRIEF)
    print("Result:", result)
    assert isinstance(result, dict), "FAIL: result is not a dict"
    for key in REQUIRED_KEYS:
        assert key in result, f"FAIL: missing key '{key}'"
    print("TEST 1 PASSED")

async def test_2_values_make_sense():
    print("\n--- TEST 2: Values are correct types and sensible ---")
    result = await parse_brief(BRIEF)
    assert isinstance(result["product_name"], str) and len(result["product_name"]) > 0
    assert isinstance(result["special_offers"], list) and len(result["special_offers"]) > 0, \
        "FAIL: special_offers should have at least 1 item (the female senior citizen bonus)"
    assert isinstance(result["include_inactive"], bool), \
        "FAIL: include_inactive must be a bool"
    assert result["include_inactive"] == True, \
        "FAIL: brief says don't skip inactive — should be True"
    assert "superbfsi.com" in result["cta_url"], \
        "FAIL: cta_url should contain the SuperBFSI URL"
    assert result["optimization_goal"] in ("open_rate", "click_rate", "both"), \
        f"FAIL: unexpected optimization_goal: {result['optimization_goal']}"
    print(f"  product_name:       {result['product_name']}")
    print(f"  special_offers:     {result['special_offers']}")
    print(f"  include_inactive:   {result['include_inactive']}")
    print(f"  optimization_goal:  {result['optimization_goal']}")
    print(f"  cta_url:            {result['cta_url']}")
    print("TEST 2 PASSED")

async def test_3_logged_to_db():
    print("\n--- TEST 3: Output was logged to agent_logs table ---")
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog
    db = SessionLocal()
    log = db.query(AgentLog).filter(AgentLog.agent_name == "brief_parser").first()
    db.close()
    assert log is not None, "FAIL: no log entry found for brief_parser"
    assert log.input_data is not None
    assert log.output_data is not None
    print(f"  Log found — agent: {log.agent_name}, iteration: {log.iteration}")
    print("TEST 3 PASSED")

async def run_all():
    tests = [test_1_returns_dict, test_2_values_make_sense, test_3_logged_to_db]
    passed = 0
    for test_fn in tests:
        try:
            await test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}")
            print("--- STOPPED: fix this before continuing ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {test_fn.__name__}: {type(e).__name__}: {e}")
            break

    print(f"\n{'='*40}")
    print(f"Results: {passed}/3 tests passed")
    if passed == 3:
        print("ALL TESTS PASSED — Sub-phase 2 complete")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())