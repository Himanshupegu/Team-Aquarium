"""
agents/orchestrator.py
Root coordinator that wires all agents into a single pipeline
with human-in-the-loop approval.

Usage:
    orchestrator = Orchestrator()
    state = CampaignState(campaign_brief="Run email campaign for XDeposit...")
    state = await orchestrator.run(state)       # pauses at awaiting_approval
    state = await orchestrator.resume(state, "approve")  # continues execution
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.agents.brief_parser import parse_brief
from backend.agents.profiler import CustomerProfiler
from backend.agents.content_gen import generate_content
from backend.agents.executor import execute_campaigns, build_send_time
from backend.agents.analyst import analyze_performance
from backend.agents.optimizer import decide_next_iteration
from backend.tools.api_tools import call_tool_by_name


# ═══════════════════════════════════════════════════════════════════════════
# CAMPAIGN STATE
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CampaignState:
    campaign_brief: str
    max_iterations: int = 3
    status: str = "idle"
    iteration: int = 0
    parsed_brief: dict = field(default_factory=dict)
    all_segments: dict = field(default_factory=dict)
    segments_used: list[str] = field(default_factory=list)
    pending_variants: list[dict] = field(default_factory=list)
    all_results: list[dict] = field(default_factory=list)
    sent_campaigns: list[dict] = field(default_factory=list)
    human_decision: str | None = None       # "approve" or "reject"
    human_feedback: str = ""
    next_segments: list[str] = field(default_factory=list)
    optimization_notes: str = ""
    error: str | None = None
    final_summary: dict = field(default_factory=dict)
    cohort_ids: set = field(default_factory=set)
    _profiler: object = field(default=None, repr=False)


# ═══════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL STATE STORE
# ═══════════════════════════════════════════════════════════════════════════

_active_states: dict[str, CampaignState] = {}


def get_state(campaign_id: str) -> CampaignState | None:
    return _active_states.get(campaign_id)


def save_state(campaign_id: str, state: CampaignState):
    _active_states[campaign_id] = state


# ═══════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════

class Orchestrator:
    """
    Wires all agents into a sequential pipeline:
      parse_brief → profile → generate (A/B) → [human approval] →
      execute → analyze → optimize → loop or done
    """

    def __init__(self):
        pass  # all state lives on CampaignState

    # ──────────────────────────────────────────────────────────────────────
    # MAIN RUN — Steps 1-3 (pauses at awaiting_approval)
    # ──────────────────────────────────────────────────────────────────────

    async def run(self, state: CampaignState) -> CampaignState:
        """
        Run the pipeline from the beginning. Pauses after content generation
        at status="awaiting_approval" for human review.
        """
        try:
            # ── Step 1: Parse brief ──────────────────────────────────────
            state.status = "parsing"
            print(f"[orchestrator] Step 1: Parsing campaign brief...")
            state.parsed_brief = await parse_brief(state.campaign_brief)
            print(f"[orchestrator] Brief parsed: product={state.parsed_brief.get('product_name')}")

            # ── Step 2: Load cohort and profile ──────────────────────────
            state.status = "profiling"
            print("[orchestrator] Step 2: Loading cohort and profiling segments...")
            cohort_result = call_tool_by_name("get_customer_cohort")
            cohort = cohort_result.get("data", [])
            state.cohort_ids = {c["customer_id"] for c in cohort}
            print(f"[orchestrator] Cohort loaded: {len(cohort)} customers")

            profiler = CustomerProfiler(cohort)
            state.all_segments = await profiler.get_all_segments(state.parsed_brief)
            state._profiler = profiler
            print(f"[orchestrator] {len(state.all_segments)} segments created")

            # Pick initial segments: top 2 by size
            sorted_segs = sorted(
                state.all_segments.items(),
                key=lambda x: x[1].size,
                reverse=True,
            )
            state.next_segments = [label for label, _ in sorted_segs[:2]]
            print(f"[orchestrator] Initial segments: {state.next_segments}")

            # ── Step 3: Enter main loop (first iteration) ────────────────
            state = await self._generate_variants(state)
            return state  # paused at awaiting_approval

        except Exception as e:
            state.status = "error"
            state.error = str(e)
            print(f"[orchestrator] ERROR in run(): {type(e).__name__}: {e}")
            return state

    # ──────────────────────────────────────────────────────────────────────
    # RESUME — After human approval (Steps 4-7)
    # ──────────────────────────────────────────────────────────────────────

    async def resume(
        self,
        state: CampaignState,
        decision: str,
        feedback: str = "",
    ) -> CampaignState:
        """
        Resume after human review.

        Args:
            state: Current campaign state (status should be "awaiting_approval")
            decision: "approve" or "reject"
            feedback: Optional feedback text (used on reject to guide regeneration)
        """
        try:
            state.human_decision = decision
            state.human_feedback = feedback

            # ── Step 4: Handle decision ──────────────────────────────────
            if decision == "reject":
                print(f"[orchestrator] Human rejected. Feedback: {feedback}")
                state = await self._regenerate_with_feedback(state)
                return state  # back to awaiting_approval

            if decision != "approve":
                state.status = "error"
                state.error = f"Unknown decision: {decision}. Expected 'approve' or 'reject'."
                return state

            print("[orchestrator] Human approved. Continuing execution...")

            # ── Step 5: Execute ──────────────────────────────────────────
            state.status = "executing"
            print(f"[orchestrator] Step 5: Executing {len(state.pending_variants)} variants...")
            exec_result = await execute_campaigns(
                state.pending_variants,
                state.iteration,
                state.cohort_ids,
            )
            state.sent_campaigns.extend(exec_result["sent"])
            state.pending_variants = []
            print(f"[orchestrator] {len(exec_result['sent'])} sent, "
                  f"{len(exec_result['failed'])} failed")

            # ── Step 6: Analyze ──────────────────────────────────────────
            state.status = "analyzing"
            print("[orchestrator] Step 6: Analyzing performance...")
            if exec_result["sent"]:
                analysis = await analyze_performance(exec_result["sent"], state.iteration)
                # Tag results with iteration for optimizer
                for r in analysis["results"]:
                    r["iteration"] = state.iteration
                state.all_results.extend(analysis["results"])
                print(f"[orchestrator] Analysis complete: "
                      f"open_rate={analysis['overall_open_rate']}, "
                      f"click_rate={analysis['overall_click_rate']}")
            else:
                print("[orchestrator] No campaigns sent — skipping analysis")

            # ── Step 7: Optimize ─────────────────────────────────────────
            state.status = "optimizing"
            print("[orchestrator] Step 7: Deciding next iteration...")
            state.segments_used.extend(state.next_segments)

            opt_decision = await decide_next_iteration(
                all_results=state.all_results,
                segments_used=state.segments_used,
                all_segments=state.all_segments,
                iteration=state.iteration,
                max_iterations=state.max_iterations,
                campaign_brief=state.parsed_brief,
            )
            state.optimization_notes = opt_decision.get("optimization_notes", "")

            if opt_decision["should_continue"]:
                state.next_segments = opt_decision["next_segments"]
                print(f"[orchestrator] Continuing to iteration {state.iteration + 1} "
                      f"with segments: {state.next_segments}")
                # Loop back to Step 3
                state = await self._generate_variants(state)
                return state  # paused at awaiting_approval again
            else:
                # Done — build final summary
                state.status = "done"
                state.final_summary = self._build_final_summary(state)
                print(f"[orchestrator] Campaign complete: {opt_decision['stop_reason']}")
                print(f"[orchestrator] Final summary: {state.final_summary}")
                return state

        except Exception as e:
            state.status = "error"
            state.error = str(e)
            print(f"[orchestrator] ERROR in resume(): {type(e).__name__}: {e}")
            return state

    # ══════════════════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ══════════════════════════════════════════════════════════════════════

    async def _generate_variants(self, state: CampaignState) -> CampaignState:
        """Step 3: Generate A/B variants for each segment, then pause."""
        state.iteration += 1
        state.status = "generating"
        state.pending_variants = []
        state.human_decision = None
        state.human_feedback = ""

        print(f"[orchestrator] Step 3: Generating content for iteration {state.iteration}, "
              f"segments: {state.next_segments}")

        # Build previous performance for content gen context
        prev_performance = []
        if state.iteration > 1 and state.all_results:
            prev_performance = [
                {
                    "segment": r.get("segment_label", "?"),
                    "variant": r.get("variant_label", "?"),
                    "open_rate": r.get("open_rate", 0),
                    "click_rate": r.get("click_rate", 0),
                }
                for r in state.all_results
            ]

        for seg_label in state.next_segments:
            segment = state.all_segments.get(seg_label)
            if not segment:
                print(f"[orchestrator] WARNING: Segment '{seg_label}' not found, skipping")
                continue

            # A/B split
            group_a, group_b = state._profiler.ab_split(segment)
            send_time = build_send_time(segment.recommended_send_hour)

            # Generate variant A
            print(f"[orchestrator] Generating variant A for '{seg_label}'...")
            content_a = await generate_content(
                parsed_brief=state.parsed_brief,
                segment=segment,
                variant_label="A",
                iteration=state.iteration,
                prev_performance=prev_performance,
            )
            state.pending_variants.append({
                "variant_label": "A",
                "segment_label": seg_label,
                "subject": content_a["subject"],
                "body": content_a["body"],
                "customer_ids": group_a,
                "send_time": send_time,
                "strategy_notes": content_a["strategy_notes"],
            })

            # Generate variant B
            print(f"[orchestrator] Generating variant B for '{seg_label}'...")
            content_b = await generate_content(
                parsed_brief=state.parsed_brief,
                segment=segment,
                variant_label="B",
                iteration=state.iteration,
                prev_performance=prev_performance,
            )
            state.pending_variants.append({
                "variant_label": "B",
                "segment_label": seg_label,
                "subject": content_b["subject"],
                "body": content_b["body"],
                "customer_ids": group_b,
                "send_time": send_time,
                "strategy_notes": content_b["strategy_notes"],
            })

        state.status = "awaiting_approval"
        print(f"[orchestrator] {len(state.pending_variants)} variants generated. "
              f"Awaiting human approval...")
        return state

    async def _regenerate_with_feedback(self, state: CampaignState) -> CampaignState:
        """Re-generate content with human feedback appended to the brief."""
        state.status = "generating"
        state.pending_variants = []
        state.human_decision = None

        # Augment the parsed brief with feedback
        augmented_brief = dict(state.parsed_brief)
        augmented_brief["human_feedback"] = state.human_feedback
        if state.human_feedback:
            existing_notes = augmented_brief.get("target_audience_notes", "")
            augmented_brief["target_audience_notes"] = (
                f"{existing_notes} [Human feedback: {state.human_feedback}]"
            ).strip()

        print(f"[orchestrator] Regenerating variants with feedback: {state.human_feedback}")

        prev_performance = [
            {
                "segment": r.get("segment_label", "?"),
                "variant": r.get("variant_label", "?"),
                "open_rate": r.get("open_rate", 0),
                "click_rate": r.get("click_rate", 0),
            }
            for r in state.all_results
        ] if state.all_results else []

        for seg_label in state.next_segments:
            segment = state.all_segments.get(seg_label)
            if not segment:
                continue

            group_a, group_b = state._profiler.ab_split(segment)
            send_time = build_send_time(segment.recommended_send_hour)

            content_a = await generate_content(
                parsed_brief=augmented_brief,
                segment=segment,
                variant_label="A",
                iteration=state.iteration,
                prev_performance=prev_performance,
            )
            state.pending_variants.append({
                "variant_label": "A",
                "segment_label": seg_label,
                "subject": content_a["subject"],
                "body": content_a["body"],
                "customer_ids": group_a,
                "send_time": send_time,
                "strategy_notes": content_a["strategy_notes"],
            })

            content_b = await generate_content(
                parsed_brief=augmented_brief,
                segment=segment,
                variant_label="B",
                iteration=state.iteration,
                prev_performance=prev_performance,
            )
            state.pending_variants.append({
                "variant_label": "B",
                "segment_label": seg_label,
                "subject": content_b["subject"],
                "body": content_b["body"],
                "customer_ids": group_b,
                "send_time": send_time,
                "strategy_notes": content_b["strategy_notes"],
            })

        state.status = "awaiting_approval"
        print(f"[orchestrator] {len(state.pending_variants)} variants regenerated. "
              f"Awaiting human approval...")
        return state

    def _build_final_summary(self, state: CampaignState) -> dict:
        """Build the final campaign summary."""
        total_customers = sum(
            s.get("customer_count", 0) for s in state.sent_campaigns
        )

        best_overall = {}
        if state.all_results:
            best_overall = max(
                state.all_results,
                key=lambda r: r.get("composite_score", 0),
            )

        total_opens = sum(r.get("opens", 0) for r in state.all_results)
        total_clicks = sum(r.get("clicks", 0) for r in state.all_results)
        total_sent = sum(r.get("total_sent", 0) for r in state.all_results)

        return {
            "total_campaigns_sent": len(state.sent_campaigns),
            "total_customers_reached": total_customers,
            "iterations_completed": state.iteration,
            "segments_targeted": state.segments_used,
            "best_overall": best_overall,
            "overall_open_rate": round(total_opens / total_sent, 4) if total_sent else 0.0,
            "overall_click_rate": round(total_clicks / total_sent, 4) if total_sent else 0.0,
        }
