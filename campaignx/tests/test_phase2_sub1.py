import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tools.api_tools import (
    get_registry,
    call_tool_by_name,
    check_budget,
    get_tool_descriptions,
    get_budget_status,
)
from backend.db.session import SessionLocal
from backend.db.models import ApiUsageTracker
from datetime import datetime

# ─────────────────────────────────────────────────────
# TEST 1 — Spec is reachable and has 3 expected paths
# ─────────────────────────────────────────────────────
def test_1_spec_fetch():
    print("\n--- TEST 1: Spec Fetch ---")
    registry = get_registry()
    paths = [entry["path"] for entry in registry.values()]
    print("Paths found:", paths)
    assert any("cohort" in p for p in paths), "FAIL: cohort endpoint missing"
    assert any("send"   in p for p in paths), "FAIL: send_campaign endpoint missing"
    assert any("report" in p for p in paths), "FAIL: get_report endpoint missing"
    print("TEST 1 PASSED")

# ─────────────────────────────────────────────────────
# TEST 2 — Registry builds with 3+ tools
# ─────────────────────────────────────────────────────
def test_2_registry():
    print("\n--- TEST 2: Tool Registry ---")
    registry = get_registry()
    print("Registered tools:")
    for op_id, tool in registry.items():
        print(f"  {op_id}  ->  {tool['method']} {tool['path']}")
    assert len(registry) >= 3, f"FAIL: expected 3+ tools, got {len(registry)}"
    print("TEST 2 PASSED")

# ─────────────────────────────────────────────────────
# TEST 3 — Cohort fetch returns customers + all 18 fields
# ─────────────────────────────────────────────────────
def test_3_cohort():
    print("\n--- TEST 3: Cohort Fetch ---")
    EXPECTED_FIELDS = [
        "customer_id", "Full_name", "email", "Age", "Gender",
        "Marital_Status", "Family_Size", "Dependent count", "Occupation",
        "Occupation type", "Monthly_Income", "KYC status", "City",
        "Kids_in_Household", "App_Installed", "Existing Customer",
        "Credit score", "Social_Media_Active",
    ]
    result = call_tool_by_name("get_customer_cohort")
    customers = result.get("data", [])
    print("Total customers:", result.get("total_count"))
    assert len(customers) > 0, "FAIL: no customers returned"
    for field in EXPECTED_FIELDS:
        assert field in customers[0], f"FAIL: missing field '{field}'"
    print(f"All 18 fields confirmed. Total: {result['total_count']}")
    print("TEST 3 PASSED")

# ─────────────────────────────────────────────────────
# TEST 4 — Budget counter is working in the DB
# ─────────────────────────────────────────────────────
def test_4_budget():
    print("\n--- TEST 4: Budget Tracking ---")
    status = get_budget_status()
    print(f"Budget status: {status}")
    assert status["remaining"] > 0, "FAIL: no calls remaining"
    assert status["used"] + status["remaining"] == 100, \
        f"FAIL: {status['used']} + {status['remaining']} != 100"
    print("TEST 4 PASSED")

# ─────────────────────────────────────────────────────
# TEST 5 — Short names resolve + descriptions available
# ─────────────────────────────────────────────────────
def test_5_short_names():
    print("\n--- TEST 5: Short Name Resolution + Descriptions ---")
    result = call_tool_by_name("get_customer_cohort")
    assert result.get("response_code") == 200, \
        f"FAIL: bad response code — got {result.get('response_code')}"
    print("Short name 'get_customer_cohort' resolved correctly")

    descriptions = get_tool_descriptions()
    print(f"Tool descriptions available: {len(descriptions)}")
    for t in descriptions:
        print(f"  {t['name']}  |  {t['method']}  |  {t['path']}")
    assert len(descriptions) >= 3, "FAIL: expected 3+ descriptions"
    print("TEST 5 PASSED")

# ─────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────
def run_all():
    tests = [
        test_1_spec_fetch,
        test_2_registry,
        test_3_cohort,
        test_4_budget,
        test_5_short_names,
    ]
    passed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}")
            print("--- STOPPED: fix this before continuing ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {test_fn.__name__}: {type(e).__name__}: {e}")
            break

    print(f"\n{'='*40}")
    print(f"Results: {passed}/5 tests passed")
    if passed == 5:
        print("ALL TESTS PASSED — Sub-phase 1 complete")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    run_all()
