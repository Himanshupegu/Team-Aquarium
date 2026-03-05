import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.optimizer import decide_next_iteration
from backend.agents.profiler import Segment
from dataclasses import dataclass, field

def make_segment(label, size=100):
    return Segment(
        label=label,
        customer_ids=[f"CUST{i:04d}" for i in range(size)],
        description=f"Test segment {label}",
        recommended_tone="friendly",
        recommended_send_hour=10,
        key_usp="Test USP",
        persona_hint="Test persona"
    )

ALL_SEGMENTS = {
    "female_senior_citizens": make_segment("female_senior_citizens", 698),
    "high_income_earners":    make_segment("high_income_earners", 3732),
    "young_adults":           make_segment("young_adults", 201),
    "existing_customers":     make_segment("existing_customers", 184),
    "other_customers":        make_segment("other_customers", 185),
}

SAMPLE_RESULTS = [
    {"variant_label": "A", "segment_label": "female_senior_citizens",
     "composite_score": 0.35, "open_rate": 0.4, "click_rate": 0.3},
    {"variant_label": "B", "segment_label": "female_senior_citizens",
     "composite_score": 0.28, "open_rate": 0.35, "click_rate": 0.24},
]

BRIEF = {"product_name": "XDeposit", "optimization_goal": "both",
         "key_message": "Higher returns", "tone": "professional"}

async def test_1_stops_at_max_iterations():
    print("\n--- TEST 1: Stops when max_iterations reached ---")
    result = await decide_next_iteration(
        all_results=SAMPLE_RESULTS,
        segments_used=["female_senior_citizens"],
        all_segments=ALL_SEGMENTS,
        iteration=3,
        max_iterations=3,
        campaign_brief=BRIEF
    )
    print(f"  should_continue: {result['should_continue']}")
    print(f"  stop_reason: {result['stop_reason']}")
    assert result["should_continue"] == False, "FAIL: should have stopped"
    assert result["stop_reason"] == "max_iterations_reached", \
        f"FAIL: wrong stop_reason: {result['stop_reason']}"
    print("TEST 1 PASSED")

async def test_2_continues_when_all_segments_covered():
    print("\n--- TEST 2: Continues to re-target when all segments used ---")
    result = await decide_next_iteration(
        all_results=SAMPLE_RESULTS,
        segments_used=list(ALL_SEGMENTS.keys()),
        all_segments=ALL_SEGMENTS,
        iteration=2,
        max_iterations=5,
        campaign_brief=BRIEF
    )
    print(f"  should_continue: {result['should_continue']}")
    print(f"  next_segments: {result['next_segments']}")
    print(f"  stop_reason: {result['stop_reason']}")
    assert result["should_continue"] == True, \
        "FAIL: should continue to re-target worst performers, not stop"
    assert result["stop_reason"] is None, \
        f"FAIL: stop_reason should be None, got {result['stop_reason']}"
    assert len(result["next_segments"]) > 0, \
        "FAIL: no next segments chosen for re-targeting"
    print("TEST 2 PASSED")

async def test_3_continues_and_picks_next_segments():
    print("\n--- TEST 3: Continues and picks largest unused segments ---")
    result = await decide_next_iteration(
        all_results=SAMPLE_RESULTS,
        segments_used=["female_senior_citizens"],
        all_segments=ALL_SEGMENTS,
        iteration=1,
        max_iterations=5,
        campaign_brief=BRIEF
    )
    print(f"  should_continue: {result['should_continue']}")
    print(f"  next_segments: {result['next_segments']}")
    print(f"  optimization_notes: {result['optimization_notes'][:80]}...")
    assert result["should_continue"] == True, "FAIL: should continue"
    assert len(result["next_segments"]) > 0, "FAIL: no next segments chosen"
    assert len(result["next_segments"]) <= 2, "FAIL: too many segments chosen"
    assert "female_senior_citizens" not in result["next_segments"], \
        "FAIL: already-used segment chosen again when unused ones exist"
    assert result["next_segments"][0] == "high_income_earners", \
        f"FAIL: expected high_income_earners first (largest unused), got {result['next_segments'][0]}"
    print("TEST 3 PASSED")

async def test_4_optimization_notes_not_empty():
    print("\n--- TEST 4: optimization_notes is populated ---")
    result = await decide_next_iteration(
        all_results=SAMPLE_RESULTS,
        segments_used=["female_senior_citizens"],
        all_segments=ALL_SEGMENTS,
        iteration=1,
        max_iterations=5,
        campaign_brief=BRIEF
    )
    assert isinstance(result["optimization_notes"], str), "FAIL: not a string"
    assert len(result["optimization_notes"]) > 20, "FAIL: notes too short"
    print(f"  Notes: {result['optimization_notes'][:100]}...")
    print("TEST 4 PASSED")

async def test_5_logged_to_db():
    print("\n--- TEST 5: Decision logged to agent_logs ---")
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog
    db = SessionLocal()
    log = db.query(AgentLog).filter(AgentLog.agent_name == "optimizer").first()
    db.close()
    assert log is not None, "FAIL: no log entry for optimizer"
    print(f"  Log found — agent: {log.agent_name}, iteration: {log.iteration}")
    print("TEST 5 PASSED")

async def run_all():
    tests = [
        test_1_stops_at_max_iterations,
        test_2_continues_when_all_segments_covered,
        test_3_continues_and_picks_next_segments,
        test_4_optimization_notes_not_empty,
        test_5_logged_to_db,
    ]
    passed = 0
    for t in tests:
        try:
            await t()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}\n--- STOPPED ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {t.__name__}: {type(e).__name__}: {e}")
            break

    print(f"\n{'='*40}")
    print(f"Results: {passed}/5 tests passed")
    if passed == 5:
        print("ALL TESTS PASSED — Sub-phase 7 verified")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())