"""
agents/profiler.py
Hybrid customer segmentation: data analysis (Python) + strategy (LLM) + execution (Python).

Three stages:
  1. analyze_cohort_schema()  — pure Python, builds a schema dict from live cohort data
  2. generate_segment_strategy() — LLM call, returns segment definitions with criteria
  3. execute_segmentation()   — pure Python predicate engine, assigns customers to segments

Usage:
    profiler = CustomerProfiler()
    segments = await profiler.get_all_segments(parsed_brief)
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import Counter

from backend.llm.router import llm_router
from backend.tools.api_tools import call_tool_by_name


# ═══════════════════════════════════════════════════════════════════════════
# SEGMENT DATACLASS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Segment:
    label: str
    description: str
    customer_ids: list[str] = field(default_factory=list)
    priority: int = 99
    is_catch_all: bool = False
    criteria: list[dict] = field(default_factory=list)
    recommended_tone: str = "professional"
    recommended_send_hour: int = 10
    key_usp: str = ""
    persona_hint: str = ""

    @property
    def size(self) -> int:
        return len(self.customer_ids)


# ═══════════════════════════════════════════════════════════════════════════
# PREDICATE ENGINE — evaluates LLM-defined criteria against customer data
# ═══════════════════════════════════════════════════════════════════════════

def _evaluate_condition(customer: dict, condition: dict) -> bool:
    """Evaluate a single condition against a customer record."""
    field_name = condition["field"]
    op = condition["op"]
    value = condition["value"]

    # Get raw value from customer — handle missing fields gracefully
    raw = customer.get(field_name)
    if raw is None:
        return False

    # Numeric ops — try to cast to number
    if op in ("gt", "gte", "lt", "lte", "between"):
        try:
            raw = float(raw)
        except (ValueError, TypeError):
            return False

    if op == "eq":       return str(raw).strip().lower() == str(value).strip().lower()
    if op == "neq":      return str(raw).strip().lower() != str(value).strip().lower()
    if op == "gt":       return raw > float(value)
    if op == "gte":      return raw >= float(value)
    if op == "lt":       return raw < float(value)
    if op == "lte":      return raw <= float(value)
    if op == "between":  return float(value[0]) <= raw <= float(value[1])
    if op == "in":       return str(raw).strip().lower() in [str(v).strip().lower() for v in value]
    if op == "not_in":   return str(raw).strip().lower() not in [str(v).strip().lower() for v in value]
    if op == "contains": return str(value).lower() in str(raw).lower()
    return False


def _customer_matches(customer: dict, criteria: list[dict]) -> bool:
    """All conditions within a segment are AND logic."""
    return all(_evaluate_condition(customer, cond) for cond in criteria)


# ═══════════════════════════════════════════════════════════════════════════
# CUSTOMER PROFILER CLASS
# ═══════════════════════════════════════════════════════════════════════════

class CustomerProfiler:
    """
    Hybrid segmentation engine.
    Stage 1 (Python) → Stage 2 (LLM) → Stage 3 (Python)
    """

    def __init__(self, cohort: list[dict] | None = None):
        self._cohort: list[dict] = cohort or []
        self._schema: dict = {}
        self._strategy: list[dict] = []

    # ── Cohort loading ────────────────────────────────────────────────────

    def _load_cohort(self) -> list[dict]:
        """Fetch cohort from API (uses api_tools budget tracking)."""
        if self._cohort:
            return self._cohort
        print("[profiler] Fetching customer cohort via api_tools...")
        result = call_tool_by_name("get_customer_cohort")
        self._cohort = result.get("data", [])
        print(f"[profiler] Loaded {len(self._cohort)} customers")
        return self._cohort

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 1 — Analyze cohort schema (pure Python, no LLM)
    # ══════════════════════════════════════════════════════════════════════

    def analyze_cohort_schema(self) -> dict:
        """
        Sample the cohort and return a schema dict the LLM can reason over.
        Detects field types automatically — no hardcoded assumptions.
        """
        customers = self._load_cohort()
        if not customers:
            return {"total_customers": 0, "fields": {}}

        # Collect all field names from first customer
        sample = customers[0]
        skip_fields = {"customer_id", "Full_name", "email"}  # PII, not useful for segmentation

        schema: dict = {"total_customers": len(customers), "fields": {}}

        for field_name in sample.keys():
            if field_name in skip_fields:
                continue

            # Gather all values for this field
            values = [c.get(field_name) for c in customers if c.get(field_name) is not None]
            if not values:
                continue

            schema["fields"][field_name] = self._analyze_field(field_name, values)

        self._schema = schema
        print(f"[profiler] Schema analysis complete — {len(schema['fields'])} fields profiled")
        return schema

    def _analyze_field(self, field_name: str, values: list) -> dict:
        """Automatically detect field type and compute stats."""
        # Try boolean-like detection (Yes/No fields)
        str_values = [str(v).strip() for v in values]
        unique = set(s.lower() for s in str_values)

        if unique <= {"yes", "no"}:
            yes_count = sum(1 for v in str_values if v.lower() == "yes")
            return {
                "type": "boolean",
                "yes_count": yes_count,
                "no_count": len(values) - yes_count,
            }

        # Try numeric detection
        numeric_vals = []
        for v in values:
            try:
                numeric_vals.append(float(v))
            except (ValueError, TypeError):
                break
        else:
            # All values are numeric
            return self._analyze_numeric(field_name, numeric_vals)

        # Categorical
        return self._analyze_categorical(field_name, str_values)

    def _analyze_numeric(self, field_name: str, values: list[float]) -> dict:
        """Compute numeric stats with sensible bucket boundaries."""
        min_v = min(values)
        max_v = max(values)
        avg_v = sum(values) / len(values)

        result: dict = {
            "type": "numeric",
            "min": round(min_v, 1),
            "max": round(max_v, 1),
            "avg": round(avg_v, 1),
        }

        # Auto-detect meaningful buckets based on field semantics
        if "age" in field_name.lower():
            buckets = {"<35": 0, "35-59": 0, "60+": 0}
            for v in values:
                if v < 35:
                    buckets["<35"] += 1
                elif v < 60:
                    buckets["35-59"] += 1
                else:
                    buckets["60+"] += 1
            result["buckets"] = buckets

        elif "income" in field_name.lower():
            buckets = {"<35k": 0, "35k-75k": 0, "75k+": 0}
            for v in values:
                if v < 35000:
                    buckets["<35k"] += 1
                elif v <= 75000:
                    buckets["35k-75k"] += 1
                else:
                    buckets["75k+"] += 1
            result["buckets"] = buckets

        elif "credit" in field_name.lower() or "score" in field_name.lower():
            buckets = {"<700": 0, "700-749": 0, "750+": 0}
            for v in values:
                if v < 700:
                    buckets["<700"] += 1
                elif v < 750:
                    buckets["700-749"] += 1
                else:
                    buckets["750+"] += 1
            result["buckets"] = buckets

        elif "kid" in field_name.lower() or "dependent" in field_name.lower() or "family" in field_name.lower():
            zero_count = sum(1 for v in values if v == 0)
            result["zero_count"] = zero_count
            result["nonzero_count"] = len(values) - zero_count

        else:
            # Generic tercile buckets
            sorted_vals = sorted(values)
            t1 = sorted_vals[len(sorted_vals) // 3]
            t2 = sorted_vals[2 * len(sorted_vals) // 3]
            buckets = {f"<={t1}": 0, f"{t1}-{t2}": 0, f">{t2}": 0}
            for v in values:
                if v <= t1:
                    buckets[f"<={t1}"] += 1
                elif v <= t2:
                    buckets[f"{t1}-{t2}"] += 1
                else:
                    buckets[f">{t2}"] += 1
            result["buckets"] = buckets

        return result

    def _analyze_categorical(self, field_name: str, values: list[str]) -> dict:
        """Compute categorical stats."""
        counter = Counter(values)
        unique_count = len(counter)

        if "city" in field_name.lower():
            # Too many cities — show top 10 only
            top_10 = counter.most_common(10)
            return {
                "type": "categorical",
                "unique_count": unique_count,
                "top_10": [{"city": city, "count": cnt} for city, cnt in top_10],
            }

        # Standard categorical — show all values + counts
        return {
            "type": "categorical",
            "values": list(counter.keys()),
            "counts": dict(counter),
        }

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 2 — LLM-driven segment strategy
    # ══════════════════════════════════════════════════════════════════════

    async def generate_segment_strategy(self, parsed_brief: dict, schema: dict) -> list[dict]:
        """
        Ask the LLM to define optimal segments based on actual data distributions.
        Returns a list of segment dicts with criteria, tone, USP, etc.
        """
        total = schema.get("total_customers", 0)
        prompt = f"""You are a marketing strategist for SuperBFSI, an Indian BFSI company.

CAMPAIGN BRIEF:
{json.dumps(parsed_brief, indent=2)}

CUSTOMER DATABASE SCHEMA (from live data — {total} customers total):
{json.dumps(schema, indent=2)}

Your job: Define the best customer segments for this campaign.

Rules:
- Create 5 to 7 segments based on what the data actually supports
- The catch_all segment must contain fewer than 200 customers
- No single segment should contain more than 40% of the total customer base (max 400 customers)
- If a natural segment would exceed this, split into two more specific sub-segments
- Segments must be mutually exclusive and collectively exhaustive (cover all customers)
- The last segment must always be a catch-all for anyone not in earlier segments
- Base segments on the actual field values and distributions shown in the schema above
- If the brief mentions a special offer for a specific group (e.g. female senior citizens),
  that group MUST be its own highest-priority segment
- Each segment should have a meaningfully different message angle

For each segment, return:
- label: short snake_case name
- description: one sentence explaining who this is
- priority: integer starting at 1 (1 = highest priority, evaluated first)
- is_catch_all: true only for the last fallback segment
- criteria: list of field conditions (see format below)
- recommended_tone: one of formal/friendly/warm/casual/professional/aspirational/emotional
- recommended_send_hour: best hour to send in IST (0-23)
- key_usp: the single strongest message angle for this segment (one sentence)
- persona_hint: 2-3 sentence description of a typical customer in this segment,
  for use in email content generation

Criteria format — each condition is:
  {{"field": "Gender", "op": "eq", "value": "Female"}}
  {{"field": "Age", "op": "gte", "value": 60}}
  {{"field": "App_Installed", "op": "eq", "value": "Yes"}}
  {{"field": "Monthly_Income", "op": "between", "value": [35000, 75000]}}
  {{"field": "City", "op": "in", "value": ["Mumbai", "Delhi", "Bengaluru"]}}
  {{"field": "City", "op": "not_in", "value": ["Mumbai", "Delhi"]}}
  {{"field": "KYC status", "op": "contains", "value": "complete"}}

All conditions within a segment are AND logic.
Catch-all segment has empty criteria list.

Return ONLY a JSON array. No explanation, no markdown fences."""

        raw = await llm_router.call(prompt, task="structured_parse", max_tokens=3000)
        cleaned = self._strip_markdown_fences(raw)

        try:
            strategy = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"[profiler] First parse failed: {e}. Retrying...")
            retry_prompt = prompt + f"\n\nYour previous response could not be parsed as JSON. Error: {e}\nReturn ONLY a valid JSON array."
            raw = await llm_router.call(retry_prompt, task="structured_parse", max_tokens=3000)
            cleaned = self._strip_markdown_fences(raw)
            strategy = json.loads(cleaned)

        # Validate and sort by priority
        strategy = self._validate_strategy(strategy)
        self._strategy = strategy
        print(f"[profiler] LLM strategy: {len(strategy)} segments defined")
        return strategy

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove accidental ```json ... ``` wrappers."""
        text = text.strip()
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    def _validate_strategy(self, strategy: list[dict]) -> list[dict]:
        """Ensure strategy list is well-formed."""
        if not isinstance(strategy, list):
            raise ValueError(f"LLM returned {type(strategy)}, expected list")

        for seg in strategy:
            seg.setdefault("label", "unknown")
            seg.setdefault("description", "")
            seg.setdefault("priority", 99)
            seg.setdefault("is_catch_all", False)
            seg.setdefault("criteria", [])
            seg.setdefault("recommended_tone", "professional")
            seg.setdefault("recommended_send_hour", 10)
            seg.setdefault("key_usp", "")
            seg.setdefault("persona_hint", "")

        # Sort by priority (lowest number = highest priority)
        strategy.sort(key=lambda s: s["priority"])

        # Ensure at least one catch-all exists
        has_catch_all = any(s.get("is_catch_all") for s in strategy)
        if not has_catch_all:
            strategy[-1]["is_catch_all"] = True
            strategy[-1]["criteria"] = []
            print("[profiler] Warning: no catch-all found, forced last segment as catch-all")

        return strategy

    # ══════════════════════════════════════════════════════════════════════
    # STAGE 3 — Execute segmentation (pure Python predicate engine)
    # ══════════════════════════════════════════════════════════════════════

    def execute_segmentation(self, strategy: list[dict]) -> dict[str, Segment]:
        """
        Assign each customer to exactly one segment using the LLM-defined criteria.
        Processes in priority order. Uses an assigned set for mutual exclusivity.
        Catch-all gets everyone not yet assigned.
        """
        customers = self._load_cohort()
        assigned: set[str] = set()
        segments: dict[str, Segment] = {}

        # Sort by priority (should already be sorted, but ensure)
        sorted_strategy = sorted(strategy, key=lambda s: s["priority"])

        for seg_def in sorted_strategy:
            label = seg_def["label"]
            criteria = seg_def.get("criteria", [])
            is_catch_all = seg_def.get("is_catch_all", False)

            segment = Segment(
                label=label,
                description=seg_def.get("description", ""),
                priority=seg_def.get("priority", 99),
                is_catch_all=is_catch_all,
                criteria=criteria,
                recommended_tone=seg_def.get("recommended_tone", "professional"),
                recommended_send_hour=seg_def.get("recommended_send_hour", 10),
                key_usp=seg_def.get("key_usp", ""),
                persona_hint=seg_def.get("persona_hint", ""),
            )

            if is_catch_all:
                # Catch-all gets everyone not yet assigned
                segment.customer_ids = [
                    c["customer_id"] for c in customers
                    if c["customer_id"] not in assigned
                ]
            else:
                # Evaluate criteria for unassigned customers
                for c in customers:
                    cid = c["customer_id"]
                    if cid in assigned:
                        continue
                    if _customer_matches(c, criteria):
                        segment.customer_ids.append(cid)

            assigned.update(segment.customer_ids)
            segments[label] = segment
            print(f"[profiler] Segment '{label}': {segment.size} customers "
                  f"(priority={segment.priority}, catch_all={is_catch_all})")

        total_assigned = sum(s.size for s in segments.values())
        print(f"[profiler] Segmentation complete — {total_assigned}/{len(customers)} customers assigned "
              f"across {len(segments)} segments")

        return segments

    # ══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════

    async def get_all_segments(self, campaign_id: str, campaign_brief: dict) -> dict[str, Segment]:
        """
        Main entry point. Runs all three stages in order:
          1. Analyze cohort schema (Python)
          2. Generate segment strategy (LLM)
          3. Execute segmentation (Python)
          4. Log everything to agent_logs
        """
        # Stage 1
        schema = self.analyze_cohort_schema()

        # Stage 2
        strategy = await self.generate_segment_strategy(campaign_brief, schema)

        # Stage 3
        segments = self.execute_segmentation(strategy)

        # Log to DB
        self._log_to_db(campaign_id, schema, strategy, segments)

        return segments

    def summary(self) -> dict:
        """Return a summary dict of all segments for display/logging."""
        segments = {label: seg for label, seg in self.__dict__.get("_segments", {}).items()}
        # Rebuild from last run if needed
        return {
            label: {
                "size": seg.size,
                "priority": seg.priority,
                "is_catch_all": seg.is_catch_all,
                "description": seg.description,
                "recommended_tone": seg.recommended_tone,
                "key_usp": seg.key_usp,
            }
            for label, seg in segments.items()
        }

    def ab_split(self, segment: Segment, ratio: float = 0.5) -> tuple[list[str], list[str]]:
        """
        Split a segment's customer IDs into two groups for A/B testing.
        Returns (group_a, group_b).
        """
        ids = segment.customer_ids
        split_point = int(len(ids) * ratio)
        return ids[:split_point], ids[split_point:]

    # ── Logging ───────────────────────────────────────────────────────────

    def _log_to_db(self, campaign_id: str, schema: dict, strategy: list[dict], segments: dict[str, Segment]) -> None:
        """Log the full profiler run to agent_logs."""
        import json as _json
        from backend.db.session import SessionLocal
        from backend.db.models import AgentLog

        segment_summary = {
            label: {"size": seg.size, "priority": seg.priority, "is_catch_all": seg.is_catch_all}
            for label, seg in segments.items()
        }

        msg = _json.dumps({
            "iteration": 1,
            "schema_fields": list(schema.get("fields", {}).keys()),
            "total_customers": schema.get("total_customers", 0),
            "strategy": strategy,
            "segment_sizes": segment_summary,
            "reasoning": f"Hybrid segmentation: {len(schema.get('fields', {}))} fields analyzed, "
                         f"{len(strategy)} segments defined by LLM, "
                         f"{sum(s.size for s in segments.values())} customers assigned",
        })

        db = SessionLocal()
        try:
            log = AgentLog(
                created_at=datetime.now(timezone.utc),
                campaign_id=campaign_id,
                agent_name="profiler",
                message=msg,
            )
            db.add(log)
            db.commit()
            print("[profiler] Logged to agent_logs table")
        finally:
            db.close()
