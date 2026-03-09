"""
test_phase2_sub3.py — Customer Profiler (hybrid 3-stage)
Tests: schema analysis, LLM strategy, segmentation execution, mutual exclusivity, logging
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tools.api_tools import call_tool_by_name
from backend.agents.profiler import CustomerProfiler, Segment
from backend.db.session import SessionLocal, init_db
from backend.db.models import AgentLog

init_db()

# ── Shared loader ────────────────────────────────────────────────────────

async def load_cohort_and_segments():
    from backend.agents.brief_parser import parse_brief
    result = call_tool_by_name("get_customer_cohort")
    cohort = result["data"]
    brief = await parse_brief("test-id", 
        "Run email campaign for XDeposit from SuperBFSI, 1% higher returns than competitors. "
        "Additional 0.25% for female senior citizens. Include https://superbfsi.com/xdeposit/explore/"
    )
    profiler = CustomerProfiler(cohort)
    segments = await profiler.get_all_segments(brief)
    return cohort, profiler, segments


# ── Tests ─────────────────────────────────────────────────────────────────

def test_1_segments_exist(cohort, profiler, segments):
    print("\n--- TEST 1: Segments exist and are non-empty ---")
    assert len(segments) >= 4, f"FAIL: expected 4+ segments, got {len(segments)}"
    assert len(segments) <= 9, f"FAIL: expected <=9 segments, got {len(segments)}"
    for label, seg in segments.items():
        print(f"  {label}: {seg.size} customers (priority={seg.priority}, catch_all={seg.is_catch_all})")
        assert isinstance(seg, Segment), f"FAIL: {label} is not a Segment"
    print("TEST 1 PASSED")


def test_2_mutual_exclusivity(cohort, profiler, segments):
    print("\n--- TEST 2: Mutual exclusivity — no customer in two segments ---")
    all_ids = []
    for label, seg in segments.items():
        all_ids.extend(seg.customer_ids)
    assert len(all_ids) == len(set(all_ids)), \
        f"FAIL: {len(all_ids) - len(set(all_ids))} duplicate customer assignments"
    print(f"  {len(all_ids)} total assignments, all unique")
    print("TEST 2 PASSED")


def test_3_exhaustive(cohort, profiler, segments):
    print("\n--- TEST 3: Collectively exhaustive — all customers assigned ---")
    total_assigned = sum(seg.size for seg in segments.values())
    assert total_assigned == len(cohort), \
        f"FAIL: {total_assigned} assigned vs {len(cohort)} in cohort"
    print(f"  {total_assigned}/{len(cohort)} customers covered")
    print("TEST 3 PASSED")


def test_4_catch_all_exists(cohort, profiler, segments):
    print("\n--- TEST 4: Catch-all segment exists ---")
    catch_alls = [s for s in segments.values() if s.is_catch_all]
    assert len(catch_alls) >= 1, "FAIL: no catch-all segment found"
    for ca in catch_alls:
        print(f"  Catch-all: '{ca.label}' with {ca.size} customers")
    print("TEST 4 PASSED")


def test_5_segment_metadata(cohort, profiler, segments):
    print("\n--- TEST 5: Segment metadata is populated ---")
    for label, seg in segments.items():
        assert seg.recommended_tone, f"FAIL: {label} missing recommended_tone"
        assert seg.key_usp, f"FAIL: {label} missing key_usp"
        assert isinstance(seg.recommended_send_hour, int), f"FAIL: {label} send_hour not int"
        print(f"  {label}: tone={seg.recommended_tone}, send_hour={seg.recommended_send_hour}")
    print("TEST 5 PASSED")


def test_6_ab_split(cohort, profiler, segments):
    print("\n--- TEST 6: A/B split works ---")
    first_seg = list(segments.values())[0]
    if first_seg.size >= 2:
        a, b = profiler.ab_split(first_seg)
        assert len(a) + len(b) == first_seg.size, \
            f"FAIL: split sizes don't add up: {len(a)} + {len(b)} != {first_seg.size}"
        print(f"  Split '{first_seg.label}' ({first_seg.size}): A={len(a)}, B={len(b)}")
    else:
        print(f"  Skipped — '{first_seg.label}' has only {first_seg.size} customer(s)")
    print("TEST 6 PASSED")


def test_7_logged_to_db(cohort, profiler, segments):
    print("\n--- TEST 7: Output logged to agent_logs ---")
    db = SessionLocal()
    try:
        log = db.query(AgentLog).filter(
            AgentLog.agent_name == "profiler"
        ).order_by(AgentLog.timestamp.desc()).first()
        assert log is not None, "FAIL: no profiler log found"
        print(f"  Log found — agent: {log.agent_name}, iteration: {log.iteration}")
        assert "strategy" in log.output_data, "FAIL: strategy not in output_data"
        assert "segment_sizes" in log.output_data, "FAIL: segment_sizes not in output_data"
        print(f"  output_data keys: {list(log.output_data.keys())}")
    finally:
        db.close()
    print("TEST 7 PASSED")


# ── Runner ────────────────────────────────────────────────────────────────

def run_all():
    cohort, profiler, segments = asyncio.run(load_cohort_and_segments())

    tests = [
        test_1_segments_exist,
        test_2_mutual_exclusivity,
        test_3_exhaustive,
        test_4_catch_all_exists,
        test_5_segment_metadata,
        test_6_ab_split,
        test_7_logged_to_db,
    ]
    passed = 0
    for test_fn in tests:
        try:
            test_fn(cohort, profiler, segments)
            passed += 1
        except AssertionError as e:
            print(f"\n{e}")
            print("--- STOPPED: fix this before continuing ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {test_fn.__name__}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            break

    print(f"\n{'='*40}")
    print(f"Results: {passed}/7 tests passed")
    if passed == 7:
        print("ALL TESTS PASSED — Sub-phase 3 complete")
    else:
        print("Fix the failure above and re-run")
    print("=" * 40)


if __name__ == "__main__":
    run_all()
