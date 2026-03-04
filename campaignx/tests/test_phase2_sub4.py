import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.tools.api_tools import call_tool_by_name
from backend.agents.brief_parser import parse_brief
from backend.agents.profiler import CustomerProfiler
from backend.agents.content_gen import generate_content, validate_content

BRIEF = (
    "Run email campaign for launching XDeposit, a flagship term deposit product "
    "from SuperBFSI, that gives 1 percentage point higher returns than its competitors. "
    "Announce an additional 0.25 percentage point higher returns for female senior citizens. "
    "Optimise for open rate and click rate. Don't skip emails to customers marked 'inactive'. "
    "Include the call to action: https://superbfsi.com/xdeposit/explore/."
)
CTA_URL = "https://superbfsi.com/xdeposit/explore/"

async def setup():
    parsed = await parse_brief(BRIEF)
    result = call_tool_by_name("get_customer_cohort")
    cohort = result["data"]
    profiler = CustomerProfiler(cohort)
    segments = await profiler.get_all_segments(parsed)
    return parsed, segments

async def test_1_returns_required_keys():
    print("\n--- TEST 1: Returns dict with subject, body, strategy_notes ---")
    parsed, segments = await setup()
    seg = list(segments.values())[0]
    result = await generate_content(parsed, seg, "A", 1, [])
    print(f"  subject: {result.get('subject', '')[:80]}")
    print(f"  body length: {len(result.get('body', ''))}")
    print(f"  strategy_notes: {result.get('strategy_notes', '')[:80]}")
    assert "subject" in result and len(result["subject"]) > 0, "FAIL: missing subject"
    assert "body" in result and len(result["body"]) > 0, "FAIL: missing body"
    assert "strategy_notes" in result, "FAIL: missing strategy_notes"
    print("TEST 1 PASSED")

async def test_2_content_rules():
    print("\n--- TEST 2: Content rules enforced ---")
    parsed, segments = await setup()
    seg = list(segments.values())[0]
    result = await generate_content(parsed, seg, "A", 1, [])
    subject = result["subject"]
    body = result["body"]
    assert len(subject) <= 200, f"FAIL: subject too long ({len(subject)} chars)"
    assert "http" not in subject.lower(), "FAIL: URL found in subject"
    assert CTA_URL in body, "FAIL: CTA URL missing from body"
    assert len(body) <= 5000, f"FAIL: body too long ({len(body)} chars)"
    print(f"  Subject length: {len(subject)} chars — OK")
    print(f"  CTA URL present in body — OK")
    print(f"  Body length: {len(body)} chars — OK")
    print("TEST 2 PASSED")

async def test_3_variants_differ():
    print("\n--- TEST 3: Variant A and B produce different content ---")
    parsed, segments = await setup()
    seg = list(segments.values())[0]
    result_a = await generate_content(parsed, seg, "A", 1, [])
    result_b = await generate_content(parsed, seg, "B", 1, [])
    print(f"  Variant A subject: {result_a['subject'][:60]}")
    print(f"  Variant B subject: {result_b['subject'][:60]}")
    assert result_a["subject"] != result_b["subject"], \
        "FAIL: Variants A and B have identical subjects"
    print("TEST 3 PASSED")

async def test_4_female_seniors_mentions_bonus():
    print("\n--- TEST 4: female_seniors content mentions 0.25% bonus ---")
    parsed, segments = await setup()
    female_seg = next(
        (s for s in segments.values() if "female" in s.label.lower() or "senior" in s.label.lower()),
        None
    )
    if not female_seg:
        print("  SKIP: no female/senior segment found in this run")
        print("TEST 4 SKIPPED")
        return
    result = await generate_content(parsed, female_seg, "A", 1, [])
    body_lower = result["body"].lower()
    subject_lower = result["subject"].lower()
    mentions_bonus = (
        "0.25" in body_lower or
        "bonus" in body_lower or
        "additional" in body_lower or
        "exclusive" in body_lower
    )
    print(f"  Segment: {female_seg.label}")
    print(f"  Subject: {result['subject']}")
    assert mentions_bonus, \
        "FAIL: female senior content does not mention the 0.25% bonus or exclusivity"
    print("TEST 4 PASSED")

async def test_5_validate_content_function():
    print("\n--- TEST 5: validate_content catches rule violations ---")
    errors = validate_content(
        subject="Check out https://example.com right now",
        body="No CTA link here at all",
        cta_url=CTA_URL
    )
    print(f"  Errors caught: {errors}")
    assert any("url" in e.lower() or "http" in e.lower() for e in errors), \
        "FAIL: did not catch URL in subject"
    assert any("cta" in e.lower() or "url" in e.lower() or "missing" in e.lower() for e in errors), \
        "FAIL: did not catch missing CTA URL in body"

    no_errors = validate_content(
        subject="Great returns with XDeposit",
        body=f"Invest today and earn more. {CTA_URL}",
        cta_url=CTA_URL
    )
    assert no_errors == [], f"FAIL: valid content flagged as invalid: {no_errors}"
    print("  Valid content passed with no errors — OK")
    print("TEST 5 PASSED")

async def test_6_logged_to_db():
    print("\n--- TEST 6: Content generation logged to agent_logs ---")
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog
    db = SessionLocal()
    log = db.query(AgentLog).filter(AgentLog.agent_name == "content_gen").first()
    db.close()
    assert log is not None, "FAIL: no log entry found for content_gen"
    print(f"  Log found — agent: {log.agent_name}, iteration: {log.iteration}")
    print("TEST 6 PASSED")

async def run_all():
    tests = [
        test_1_returns_required_keys,
        test_2_content_rules,
        test_3_variants_differ,
        test_4_female_seniors_mentions_bonus,
        test_5_validate_content_function,
        test_6_logged_to_db,
    ]
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
    print(f"Results: {passed}/6 tests passed")
    if passed == 6:
        print("ALL TESTS PASSED — Sub-phase 4 complete")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())