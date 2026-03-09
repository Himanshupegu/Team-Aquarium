import asyncio, json, os
os.environ["MOCK_API"] = "false"

from backend.agents.orchestrator import Orchestrator, CampaignState

BRIEF = (
    "Run email campaign for launching XDeposit, a flagship term deposit product "
    "from SuperBFSI, that gives 1 percentage point higher returns than its competitors. "
    "Announce an additional 0.25 percentage point higher returns for female senior citizens. "
    "Optimise for open rate and click rate. Don't skip emails to customers marked inactive. "
    "Include the call to action: https://superbfsi.com/xdeposit/explore/"
)

async def main():
    orchestrator = Orchestrator()
    state = CampaignState(campaign_brief=BRIEF, max_iterations=3)

    print("\n[STEP 1] Starting orchestrator...")
    state = await orchestrator.run(state)
    print(f"Status: {state.status} | Pending variants: {len(state.pending_variants)}")

    iteration = 0
    while state.status == "awaiting_approval":
        iteration += 1
        print(f"\n[STEP] Auto-approving iteration {iteration}...")
        state = await orchestrator.resume(state, decision="approve")
        print(f"Status after approve: {state.status}")
        print(f"Sent so far: {len(state.sent_campaigns)}")

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(json.dumps(state.final_summary, indent=2))

    print("\n" + "="*60)
    print("ALL RESULTS (per campaign)")
    print("="*60)
    for r in state.all_results:
        print(f"  Variant {r['variant_label']} | Segment: {r['segment_label']} | "
              f"Open: {r['open_rate']*100:.1f}% | Click: {r['click_rate']*100:.1f}% | "
              f"Composite: {r['composite_score']:.4f} | Sent to: {r['total_sent']}")

    print("\n" + "="*60)
    print("SEGMENTS TARGETED")
    print("="*60)
    print(state.segments_used)

    print("\n" + "="*60)
    print("SLIDE 4 NUMBERS")
    print("="*60)
    s = state.final_summary
    best = s.get("best_overall", {})
    print(f"Total campaigns sent: {s.get('total_campaigns_sent')}")
    print(f"Total customers reached: {s.get('total_customers_reached')}")
    print(f"Iterations completed: {s.get('iterations_completed')}")
    print(f"Segments targeted: {s.get('segments_targeted')}")
    print(f"Overall open rate: {s.get('overall_open_rate')*100:.1f}%")
    print(f"Overall click rate: {s.get('overall_click_rate')*100:.1f}%")
    print(f"Best segment: {best.get('segment_label')} | Variant: {best.get('variant_label')} | "
          f"Open: {best.get('open_rate')*100:.1f}% | Click: {best.get('click_rate')*100:.1f}% | "
          f"Composite: {best.get('composite_score'):.4f}")

asyncio.run(main())
