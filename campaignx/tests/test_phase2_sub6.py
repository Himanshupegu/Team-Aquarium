import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.analyst import analyze_performance, compute_metrics
from backend.tools.api_tools import call_tool_by_name
from backend.agents.executor import execute_campaigns, build_send_time

# ── Helpers ────────────────────────────────────────────────────────────────

def get_cohort_ids():
    result = call_tool_by_name("get_customer_cohort")
    return {c["customer_id"] for c in result["data"]}, list(result["data"])

def test_1_compute_metrics_logic():
    print("\n--- TEST 1: compute_metrics calculates correctly ---")
    rows = [
        {"EO": "Y", "EC": "Y"},
        {"EO": "Y", "EC": "N"},
        {"EO": "N", "EC": "N"},
        {"EO": "N", "EC": "N"},
    ]
    m = compute_metrics(rows)
    print(f"  open_rate={m['open_rate']}  click_rate={m['click_rate']}  composite={m['composite_score']}")
    assert m["open_rate"]   == 0.5,  f"FAIL: expected 0.5, got {m['open_rate']}"
    assert m["click_rate"]  == 0.25, f"FAIL: expected 0.25, got {m['click_rate']}"
    assert m["composite_score"] == round(0.25*0.7 + 0.5*0.3, 4), "FAIL: composite formula wrong"
    assert m["opens"]  == 2
    assert m["clicks"] == 1
    assert m["total_sent"] == 4

    empty = compute_metrics([])
    assert empty["open_rate"] == 0.0
    assert empty["composite_score"] == 0.0
    print("TEST 1 PASSED")

async def test_2_full_analysis_pipeline():
    print("\n--- TEST 2: Full pipeline — send then analyze ---")
    cohort_ids, cohort = get_cohort_ids()
    sample_ids = list(cohort_ids)[:10]

    variants = [{
        "variant_label": "A",
        "segment_label": "analyst_test",
        "subject": "Better Returns with XDeposit",
        "body": "SuperBFSI XDeposit gives you 1% higher returns. Start today. https://superbfsi.com/xdeposit/explore/",
        "customer_ids": sample_ids,
        "send_time": build_send_time(10),
        "strategy_notes": "Analyst test variant"
    }]

    exec_result = await execute_campaigns(variants, iteration=98, cohort_ids=cohort_ids)
    assert len(exec_result["sent"]) == 1, f"FAIL: campaign not sent: {exec_result['failed']}"

    analysis = await analyze_performance(exec_result["sent"], iteration=98)

    print(f"  Results count: {len(analysis['results'])}")
    print(f"  Best variant: {analysis['best_variant']}")
    print(f"  Overall open_rate: {analysis['overall_open_rate']}")
    print(f"  Overall click_rate: {analysis['overall_click_rate']}")
    print(f"  Analyst summary: {analysis['analyst_summary'][:100]}...")

    assert len(analysis["results"]) == 1
    assert "best_variant" in analysis and analysis["best_variant"] is not None
    assert 0.0 <= analysis["overall_open_rate"] <= 1.0
    assert 0.0 <= analysis["overall_click_rate"] <= 1.0
    assert isinstance(analysis["analyst_summary"], str) and len(analysis["analyst_summary"]) > 20
    print("TEST 2 PASSED")

async def test_3_report_rows_saved_to_db():
    print("\n--- TEST 3: Report rows saved to campaign_reports table ---")
    from backend.db.session import SessionLocal
    from backend.db.models import CampaignReport
    db = SessionLocal()
    count = db.query(CampaignReport).count()
    db.close()
    print(f"  Total rows in campaign_reports: {count}")
    assert count > 0, "FAIL: no report rows saved to DB"
    print("TEST 3 PASSED")

async def test_4_logged_to_agent_logs():
    print("\n--- TEST 4: Analysis logged to agent_logs ---")
    from backend.db.session import SessionLocal
    from backend.db.models import AgentLog
    db = SessionLocal()
    log = db.query(AgentLog).filter(AgentLog.agent_name == "analyst").first()
    db.close()
    assert log is not None, "FAIL: no log entry for analyst"
    print(f"  Log found — agent: {log.agent_name}, iteration: {log.iteration}")
    print("TEST 4 PASSED")

def test_5_composite_score_formula():
    print("\n--- TEST 5: Composite score uses correct hackathon weights ---")
    # click_rate * 0.7 + open_rate * 0.3
    rows_high_click = [{"EO": "N", "EC": "Y"}] * 10   # 100% click, 0% open
    rows_high_open  = [{"EO": "Y", "EC": "N"}] * 10   # 0% click, 100% open
    m_click = compute_metrics(rows_high_click)
    m_open  = compute_metrics(rows_high_open)
    print(f"  High click score: {m_click['composite_score']} (expected 0.7)")
    print(f"  High open score:  {m_open['composite_score']}  (expected 0.3)")
    assert m_click["composite_score"] == 0.7, "FAIL: click weight should be 0.7"
    assert m_open["composite_score"]  == 0.3, "FAIL: open weight should be 0.3"
    print("TEST 5 PASSED")

async def run_all():
    passed = 0
    sync_tests = [test_1_compute_metrics_logic, test_5_composite_score_formula]
    async_tests = [test_2_full_analysis_pipeline, test_3_report_rows_saved_to_db, test_4_logged_to_agent_logs]

    for t in sync_tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}\n--- STOPPED ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {t.__name__}: {type(e).__name__}: {e}")
            break
    else:
        for t in async_tests:
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
        print("ALL TESTS PASSED — Sub-phase 6 complete")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())
