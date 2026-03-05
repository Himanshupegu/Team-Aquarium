import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

BASE_URL = "http://localhost:8000"

BRIEF = (
    "Run email campaign for launching XDeposit from SuperBFSI, "
    "1 percentage point higher returns than competitors. "
    "Additional 0.25% for female senior citizens. "
    "Include https://superbfsi.com/xdeposit/explore/"
)

# ─────────────────────────────────────────────────────
# HELPER — polls status endpoint until target status reached
# ─────────────────────────────────────────────────────
async def wait_for_status(campaign_id: str, target_statuses: list[str], timeout: int = 180) -> dict:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout // 3):
            await asyncio.sleep(3)
            try:
                r = await client.get(f"{BASE_URL}/api/campaign/{campaign_id}/status")
                if r.status_code == 200:
                    data = r.json()
                    print(f"    Polling... status={data.get('status')}")
                    if data.get("status") in target_statuses:
                        return data
            except Exception as e:
                print(f"    Poll error: {e}")
    raise TimeoutError(f"Status never reached {target_statuses} within {timeout}s")

# ─────────────────────────────────────────────────────
# TEST 1 — Health check
# ─────────────────────────────────────────────────────
async def test_1_health():
    print("\n--- TEST 1: Health check ---")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"FAIL: {r.status_code}"
    data = r.json()
    assert data["status"] == "ok", f"FAIL: {data}"
    print(f"  Response: {data}")
    print("TEST 1 PASSED")

# ─────────────────────────────────────────────────────
# TEST 2 — Budget endpoint
# ─────────────────────────────────────────────────────
async def test_2_budget():
    print("\n--- TEST 2: Budget endpoint ---")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/budget")
    assert r.status_code == 200, f"FAIL: {r.status_code}"
    data = r.json()
    assert "used" in data, "FAIL: missing 'used'"
    assert "remaining" in data, "FAIL: missing 'remaining'"
    assert "limit" in data, "FAIL: missing 'limit'"
    assert data["used"] + data["remaining"] == 100, \
        f"FAIL: used + remaining != 100: {data}"
    print(f"  Budget: {data}")
    print("TEST 2 PASSED")

# ─────────────────────────────────────────────────────
# TEST 3 — Tools endpoint
# ─────────────────────────────────────────────────────
async def test_3_tools():
    print("\n--- TEST 3: Tools endpoint ---")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/tools")
    assert r.status_code == 200, f"FAIL: {r.status_code}"
    tools = r.json()["tools"]
    print(f"  Tools found: {len(tools)}")
    for t in tools:
        print(f"    {t['name']}  {t['method']}  {t['path']}")
    assert len(tools) >= 3, f"FAIL: expected 3+ tools, got {len(tools)}"
    print("TEST 3 PASSED")

# ─────────────────────────────────────────────────────
# TEST 4 — Start campaign returns 202 and reaches awaiting_approval
# ─────────────────────────────────────────────────────
async def test_4_start_campaign():
    print("\n--- TEST 4: Start campaign returns 202 and reaches awaiting_approval ---")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{BASE_URL}/api/campaign/start", json={
            "campaign_brief": BRIEF,
            "max_iterations": 1
        })
    print(f"  Status code: {r.status_code}")
    assert r.status_code == 202, f"FAIL: expected 202, got {r.status_code}: {r.text}"

    data = r.json()
    campaign_id = data.get("campaign_id")
    print(f"  campaign_id: {campaign_id}")
    print(f"  Immediate status: {data.get('status')}")
    assert campaign_id, "FAIL: no campaign_id returned"

    # Poll until awaiting_approval or error
    print("  Polling for awaiting_approval...")
    final = await wait_for_status(campaign_id, ["awaiting_approval", "error"])
    print(f"  Final status: {final['status']}")

    assert final["status"] == "awaiting_approval", \
        f"FAIL: expected awaiting_approval, got '{final['status']}' — error: {final.get('error')}"
    assert len(final.get("pending_variants", [])) >= 2, \
        f"FAIL: expected 2+ pending variants, got {len(final.get('pending_variants', []))}"
    assert final.get("parsed_brief", {}).get("product_name"), \
        "FAIL: parsed_brief missing product_name"

    print(f"  Pending variants: {len(final['pending_variants'])}")
    print(f"  Segments found: {list(final.get('all_segments', {}).keys())}")
    print("TEST 4 PASSED")
    return campaign_id

# ─────────────────────────────────────────────────────
# TEST 5 — Approve campaign returns 202 and reaches done
# ─────────────────────────────────────────────────────
async def test_5_approve_campaign(campaign_id: str):
    print("\n--- TEST 5: Approve returns 202 and campaign reaches done ---")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{BASE_URL}/api/campaign/{campaign_id}/decision",
            json={"decision": "approve", "feedback": ""}
        )
    print(f"  Status code: {r.status_code}")
    assert r.status_code == 202, f"FAIL: expected 202, got {r.status_code}: {r.text}"
    print(f"  Immediate response: {r.json()}")

    # Poll until done or next awaiting_approval
    print("  Polling for done or awaiting_approval...")
    final = await wait_for_status(
        campaign_id,
        ["done", "awaiting_approval", "error"],
        timeout=180
    )
    print(f"  Final status: {final['status']}")
    print(f"  Sent campaigns: {len(final.get('sent_campaigns', []))}")
    print(f"  Results collected: {len(final.get('all_results', []))}")
    if final.get("final_summary"):
        print(f"  Final summary: {final['final_summary']}")

    assert final["status"] in ("done", "awaiting_approval"), \
        f"FAIL: unexpected status '{final['status']}' — error: {final.get('error')}"
    assert len(final.get("sent_campaigns", [])) >= 1, \
        "FAIL: no campaigns sent"
    assert final.get("error") is None, \
        f"FAIL: error occurred: {final.get('error')}"
    print("TEST 5 PASSED")

# ─────────────────────────────────────────────────────
# TEST 6 — Campaign status endpoint
# ─────────────────────────────────────────────────────
async def test_6_campaign_status(campaign_id: str):
    print("\n--- TEST 6: Campaign status endpoint ---")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/campaign/{campaign_id}/status")
    assert r.status_code == 200, f"FAIL: {r.status_code}"
    data = r.json()
    print(f"  status: {data.get('status')}")
    print(f"  iteration: {data.get('iteration')}")
    assert "status" in data, "FAIL: missing 'status'"
    assert "iteration" in data, "FAIL: missing 'iteration'"
    assert "_profiler" not in data, "FAIL: _profiler should be excluded from response"
    print("TEST 6 PASSED")

# ─────────────────────────────────────────────────────
# TEST 7 — 404 on unknown campaign
# ─────────────────────────────────────────────────────
async def test_7_unknown_campaign():
    print("\n--- TEST 7: 404 on unknown campaign_id ---")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE_URL}/api/campaign/nonexistent-id-12345/status")
    assert r.status_code == 404, f"FAIL: expected 404, got {r.status_code}"
    print(f"  Got 404 as expected")
    print("TEST 7 PASSED")

# ─────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────
async def run_all():
    print("=" * 40)
    print("Phase 3 Part A — FastAPI Endpoint Tests")
    print("Make sure server is running: uvicorn backend.main:app --reload")
    print("=" * 40)
    await asyncio.sleep(2)

    passed = 0
    campaign_id = None

    # Simple tests first
    for t in [test_1_health, test_2_budget, test_3_tools, test_7_unknown_campaign]:
        try:
            await t()
            passed += 1
        except AssertionError as e:
            print(f"\n{e}\n--- STOPPED ---")
            break
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {t.__name__}: {type(e).__name__}: {e}")
            break
    else:
        # Campaign flow tests
        try:
            campaign_id = await test_4_start_campaign()
            passed += 1
        except (AssertionError, TimeoutError) as e:
            print(f"\n{e}\n--- STOPPED ---")
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in test_4: {type(e).__name__}: {e}")

        if campaign_id:
            try:
                await test_5_approve_campaign(campaign_id)
                passed += 1
            except (AssertionError, TimeoutError) as e:
                print(f"\n{e}\n--- STOPPED ---")
            except Exception as e:
                print(f"\nUNEXPECTED ERROR in test_5: {type(e).__name__}: {e}")

            try:
                await test_6_campaign_status(campaign_id)
                passed += 1
            except AssertionError as e:
                print(f"\n{e}\n--- STOPPED ---")
            except Exception as e:
                print(f"\nUNEXPECTED ERROR in test_6: {type(e).__name__}: {e}")

    print(f"\n{'='*40}")
    print(f"Results: {passed}/7 tests passed")
    if passed == 7:
        print("ALL TESTS PASSED — Phase 3 Part A complete")
    else:
        print("Fix failures above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())