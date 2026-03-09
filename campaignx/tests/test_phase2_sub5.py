import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.executor import execute_campaigns, build_send_time, sanitize_customer_ids
from backend.tools.api_tools import call_tool_by_name

async def get_cohort_ids():
    result = call_tool_by_name("get_customer_cohort")
    return {c["customer_id"] for c in result["data"]}

def test_1_build_send_time():
    print("\n--- TEST 1: build_send_time format is correct ---")
    result = build_send_time(10)
    print(f"  send_time: {result}")
    parts = result.split(" ")
    assert len(parts) == 2, "FAIL: expected 'DD:MM:YY HH:MM:SS' format"
    date_parts = parts[0].split(":")
    time_parts = parts[1].split(":")
    assert len(date_parts) == 3, "FAIL: date part malformed"
    assert len(time_parts) == 3, "FAIL: time part malformed"
    assert len(date_parts[2]) == 2, f"FAIL: year must be 2 digits, got '{date_parts[2]}'"
    assert int(time_parts[0]) == 10, f"FAIL: hour should be 10, got {time_parts[0]}"
    print(f"  Format correct. Year digits: {len(date_parts[2])}")
    print("TEST 1 PASSED")

def test_2_sanitize_ids():
    print("\n--- TEST 2: sanitize_customer_ids filters and deduplicates ---")
    cohort_ids = {"CUST001", "CUST002", "CUST003"}
    dirty = ["CUST001", "CUST001", "CUST002", "FAKE999", "CUST003"]
    clean = sanitize_customer_ids(dirty, cohort_ids)
    print(f"  Input: {dirty}")
    print(f"  Output: {clean}")
    assert "FAKE999" not in clean, "FAIL: invalid ID not removed"
    assert len(clean) == len(set(clean)), "FAIL: duplicates not removed"
    assert len(clean) == 3, f"FAIL: expected 3 valid IDs, got {len(clean)}"
    print("TEST 2 PASSED")

async def test_3_sends_real_campaign():
    print("\n--- TEST 3: Sends a real campaign and returns campaign_id ---")
    cohort_ids = await get_cohort_ids()
    sample_ids = list(cohort_ids)[:5]

    from datetime import datetime, timedelta, timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    send_time = build_send_time(10)

    variants = [{
        "variant_label": "A",
        "segment_label": "test_segment",
        "subject": "Test XDeposit Campaign",
        "body": f"Earn more with XDeposit from SuperBFSI. Higher returns guaranteed. https://superbfsi.com/xdeposit/explore/",
        "customer_ids": sample_ids,
        "send_time": send_time,
        "strategy_notes": "Test send for executor validation"
    }]

    result = await execute_campaigns(variants, iteration=99, cohort_ids=cohort_ids)
    print(f"  Sent: {result['sent']}")
    print(f"  Failed: {result['failed']}")
    assert len(result["sent"]) == 1, f"FAIL: expected 1 sent, got {len(result['sent'])}"
    assert len(result["failed"]) == 0, f"FAIL: unexpected failures: {result['failed']}"
    campaign_id = result["sent"][0]["campaign_id"]
    assert campaign_id, "FAIL: no campaign_id returned"
    print(f"  campaign_id: {campaign_id}")
    print("TEST 3 PASSED")
    return campaign_id

async def test_4_saved_to_db(campaign_id: str):
    print("\n--- TEST 4: Campaign saved to database ---")
    from backend.db.session import SessionLocal
    from backend.db.models import Campaign
    db = SessionLocal()
    row = db.query(Campaign).filter(Campaign.campaign_id == campaign_id).first()
    db.close()
    assert row is not None, f"FAIL: campaign {campaign_id} not found in DB"
    assert row.variant_label == "A"
    assert row.segment_label == "test_segment"
    assert row.iteration == 99
    print(f"  DB row found — id: {row.campaign_id[:8]}..., variant: {row.variant_label}")
    print("TEST 4 PASSED")

async def test_5_invalid_ids_filtered():
    print("\n--- TEST 5: Variants with all invalid IDs are skipped ---")
    cohort_ids = await get_cohort_ids()
    variants = [{
        "variant_label": "X",
        "segment_label": "fake_segment",
        "subject": "Should not send",
        "body": f"This should not be sent. https://superbfsi.com/xdeposit/explore/",
        "customer_ids": ["FAKE001", "FAKE002", "FAKE003"],
        "send_time": build_send_time(10),
        "strategy_notes": "All IDs invalid"
    }]
    result = await execute_campaigns(variants, iteration=99, cohort_ids=cohort_ids)
    print(f"  Sent: {result['sent']}")
    print(f"  Failed: {result['failed']}")
    assert len(result["sent"]) == 0, "FAIL: should not have sent with all invalid IDs"
    print("TEST 5 PASSED")

async def run_all():
    tests_sync = [test_1_build_send_time, test_2_sanitize_ids]
    tests_async = [test_3_sends_real_campaign, test_5_invalid_ids_filtered]

    passed = 0
    campaign_id = None

    for t in tests_sync:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}")
            print("--- STOPPED ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {t.__name__}: {type(e).__name__}: {e}")
            break
    else:
        try:
            campaign_id = await test_3_sends_real_campaign()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}\n--- STOPPED ---")
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in test_3: {type(e).__name__}: {e}")

        if campaign_id:
            try:
                await test_4_saved_to_db(campaign_id)
                passed += 1
            except AssertionError as e:
                print(f"\n{e}\n--- STOPPED ---")
            except Exception as e:
                print(f"\nUNEXPECTED ERROR in test_4: {type(e).__name__}: {e}")

        try:
            await test_5_invalid_ids_filtered()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}\n--- STOPPED ---")
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in test_5: {type(e).__name__}: {e}")

    print(f"\n{'='*40}")
    print(f"Results: {passed}/5 tests passed")
    if passed == 5:
        print("ALL TESTS PASSED — Sub-phase 5 complete")
    else:
        print("Fix the failure above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())
