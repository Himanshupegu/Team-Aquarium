import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.orchestrator import Orchestrator, CampaignState, get_state, save_state

BRIEF = (
    "Run email campaign for launching XDeposit, a flagship term deposit product "
    "from SuperBFSI, that gives 1 percentage point higher returns than its competitors. "
    "Announce an additional 0.25 percentage point higher returns for female senior citizens. "
    "Optimise for open rate and click rate. Don't skip emails to customers marked inactive. "
    "Include the call to action: https://superbfsi.com/xdeposit/explore/."
)

async def test_1_reaches_awaiting_approval():
    print("\n--- TEST 1: Pipeline runs to awaiting_approval and pauses ---")
    orchestrator = Orchestrator()
    state = CampaignState(campaign_brief=BRIEF, max_iterations=2)

    state = await orchestrator.run(state)

    print(f"  Status: {state.status}")
    print(f"  Iteration: {state.iteration}")
    print(f"  Parsed brief product: {state.parsed_brief.get('product_name')}")
    print(f"  Segments found: {list(state.all_segments.keys())}")
    print(f"  Pending variants: {len(state.pending_variants)}")
    print(f"  Next segments: {state.next_segments}")

    assert state.status == "awaiting_approval", \
        f"FAIL: expected 'awaiting_approval', got '{state.status}'"
    assert state.error is None, f"FAIL: error occurred: {state.error}"
    assert len(state.pending_variants) >= 2, \
        f"FAIL: expected at least 2 variants (A+B), got {len(state.pending_variants)}"
    assert state.parsed_brief.get("product_name"), "FAIL: brief not parsed"
    assert len(state.all_segments) > 0, "FAIL: no segments created"
    print("TEST 1 PASSED")
    return state

async def test_2_approve_completes_iteration(state: CampaignState):
    print("\n--- TEST 2: Approving runs execute→analyze→optimize ---")
    orchestrator = Orchestrator()

    state = await orchestrator.resume(state, decision="approve")

    print(f"  Status after approve: {state.status}")
    print(f"  Sent campaigns: {len(state.sent_campaigns)}")
    print(f"  Results collected: {len(state.all_results)}")
    print(f"  Segments used: {state.segments_used}")

    assert state.status in ("awaiting_approval", "done"), \
        f"FAIL: unexpected status '{state.status}'"
    assert len(state.sent_campaigns) >= 1, "FAIL: no campaigns sent"
    assert len(state.all_results) >= 1, "FAIL: no results collected"
    assert len(state.segments_used) >= 1, "FAIL: no segments marked as used"
    assert state.error is None, f"FAIL: error: {state.error}"
    print("TEST 2 PASSED")
    return state

async def test_3_reject_regenerates_content():
    print("\n--- TEST 3: Rejecting regenerates content without re-profiling ---")
    orchestrator = Orchestrator()
    state = CampaignState(campaign_brief=BRIEF, max_iterations=2)
    state = await orchestrator.run(state)

    first_variants = [v["subject"] for v in state.pending_variants]
    print(f"  First subjects: {first_variants}")

    state = await orchestrator.resume(
        state,
        decision="reject",
        feedback="Make the subject more urgent and mention the deadline"
    )

    print(f"  Status after reject: {state.status}")
    second_variants = [v["subject"] for v in state.pending_variants]
    print(f"  Regenerated subjects: {second_variants}")

    assert state.status == "awaiting_approval", \
        f"FAIL: expected 'awaiting_approval' after reject, got '{state.status}'"
    assert len(state.pending_variants) >= 2, "FAIL: no variants after regeneration"
    assert state.human_decision is None, "FAIL: human_decision not cleared after reject"
    print("TEST 3 PASSED")
    return state

async def test_4_full_run_reaches_done():
    print("\n--- TEST 4: Full auto-approved run reaches 'done' ---")
    orchestrator = Orchestrator()
    state = CampaignState(campaign_brief=BRIEF, max_iterations=1)

    state = await orchestrator.run(state)
    assert state.status == "awaiting_approval", f"FAIL: {state.status}"

    state = await orchestrator.resume(state, decision="approve")

    print(f"  Final status: {state.status}")
    print(f"  Total sent: {len(state.sent_campaigns)}")
    print(f"  Final summary: {state.final_summary}")

    assert state.status == "done", \
        f"FAIL: expected 'done', got '{state.status}'"
    assert state.final_summary, "FAIL: final_summary is empty"
    assert "total_campaigns_sent" in state.final_summary
    assert "overall_open_rate" in state.final_summary
    assert state.error is None, f"FAIL: error: {state.error}"
    print("TEST 4 PASSED")

async def test_5_state_store():
    print("\n--- TEST 5: State store saves and retrieves correctly ---")
    state = CampaignState(campaign_brief="Test brief", max_iterations=1)
    save_state("test-run-001", state)
    retrieved = get_state("test-run-001")
    assert retrieved is not None, "FAIL: state not found"
    assert retrieved.campaign_brief == "Test brief"
    assert get_state("nonexistent") is None
    print("  State saved and retrieved correctly")
    print("TEST 5 PASSED")

async def run_all():
    passed = 0
    state_after_t1 = None
    state_after_t2 = None

    try:
        state_after_t1 = await test_1_reaches_awaiting_approval()
        passed += 1
    except Exception as e:
        print(f"\nERROR in test_1: {type(e).__name__}: {e}")
        print("--- STOPPED ---")

    if state_after_t1:
        try:
            state_after_t2 = await test_2_approve_completes_iteration(state_after_t1)
            passed += 1
        except Exception as e:
            print(f"\nERROR in test_2: {type(e).__name__}: {e}")

    try:
        await test_3_reject_regenerates_content()
        passed += 1
    except Exception as e:
        print(f"\nERROR in test_3: {type(e).__name__}: {e}")

    try:
        await test_4_full_run_reaches_done()
        passed += 1
    except Exception as e:
        print(f"\nERROR in test_4: {type(e).__name__}: {e}")

    try:
        await test_5_state_store()
        passed += 1
    except Exception as e:
        print(f"\nERROR in test_5: {type(e).__name__}: {e}")

    print(f"\n{'='*40}")
    print(f"Results: {passed}/5 tests passed")
    if passed == 5:
        print("ALL TESTS PASSED — Sub-phase 8 complete")
        print("Phase 2 is DONE. All agents built and verified.")
    else:
        print("Fix failures above and re-run")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())