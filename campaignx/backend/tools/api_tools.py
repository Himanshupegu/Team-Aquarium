"""
tools/api_tools.py
Dynamic OpenAPI tool discovery for CampaignX API.

Fetches the live OpenAPI spec at runtime, resolves $refs, and builds
a callable + registry for every endpoint (except /signup).
All agents call these tools instead of making raw HTTP requests.

Budget tracking enforces the 100-calls/day limit via the ApiUsageTracker
DB table so we never hit a 429 by surprise.
"""
import os
import httpx
import jsonref
from datetime import datetime, timezone
from typing import Any

from backend.config import CAMPAIGNX_API_KEY, CAMPAIGNX_BASE_URL, OPENAPI_SPEC_URL

# ── Mock mode for testing without spending API calls ─────────────────────
MOCK_MODE = os.getenv("MOCK_API", "false").lower() == "true"

# ── Module-level spec cache ──────────────────────────────────────────────
_cached_spec: dict | None = None
_tool_registry: dict[str, dict] = {}

DAILY_CALL_LIMIT = 100
SKIP_OPERATIONS = {"signup_api_v1_signup_post"}  # never call signup again


# ═══════════════════════════════════════════════════════════════════════════
# 1. SPEC FETCHING + CACHING
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_and_cache_spec() -> dict:
    """Fetch the OpenAPI spec once per process, resolve all $refs, cache it."""
    global _cached_spec
    if _cached_spec is not None:
        return _cached_spec

    print(f"[api_tools] Fetching OpenAPI spec from {OPENAPI_SPEC_URL}")
    resp = httpx.get(OPENAPI_SPEC_URL, timeout=15.0)
    resp.raise_for_status()
    raw = resp.json()

    # Resolve all $ref pointers so we get inline schemas
    resolved = jsonref.replace_refs(raw)
    _cached_spec = resolved
    print(f"[api_tools] Spec fetched — {len(resolved.get('paths', {}))} paths found")
    return _cached_spec


# ═══════════════════════════════════════════════════════════════════════════
# 2. BUDGET TRACKING (ApiUsageTracker DB table)
# ═══════════════════════════════════════════════════════════════════════════

from datetime import timedelta
IST = timezone(timedelta(hours=5, minutes=30))

def _today_str() -> str:
    """Current date as YYYY-MM-DD string in IST."""
    return datetime.now(IST).strftime("%Y-%m-%d")


def check_budget() -> int:
    """
    Return remaining calls today.  Raises RuntimeError if budget is exhausted.
    Opens its own DB session — safe to call from anywhere.
    """
    from backend.db.session import SessionLocal
    from backend.db.models import ApiUsageTracker

    today = _today_str()
    db = SessionLocal()
    try:
        row = db.query(ApiUsageTracker).order_by(ApiUsageTracker.id.desc()).first()
        if row:
            if row.date < today:
                # Reset for the new day in IST
                row.date = today
                row.call_count = 0
                row.last_updated = datetime.now(IST)
                db.commit()
            used = row.call_count
        else:
            used = 0
            
        remaining = DAILY_CALL_LIMIT - used
        if remaining <= 0:
            raise RuntimeError(
                f"[api_tools] Daily API budget exhausted ({used}/{DAILY_CALL_LIMIT}). "
                f"No more calls allowed today ({today})."
            )
        return remaining
    finally:
        db.close()


def increment_budget() -> int:
    """
    Increment today's usage count by 1. Returns new total.
    Opens its own DB session — safe to call from anywhere.
    """
    from backend.db.session import SessionLocal
    from backend.db.models import ApiUsageTracker

    today = _today_str()
    db = SessionLocal()
    try:
        row = db.query(ApiUsageTracker).order_by(ApiUsageTracker.id.desc()).first()
        if row:
            if row.date < today:
                row.date = today
                row.call_count = 1
            else:
                row.call_count += 1
            row.last_updated = datetime.now(IST)
        else:
            row = ApiUsageTracker(date=today, call_count=1, last_updated=datetime.now(IST))
            db.add(row)
        db.commit()
        return row.call_count
    finally:
        db.close()


def get_budget_status() -> dict:
    """Return {date, used, remaining, limit} for the current day."""
    from backend.db.session import SessionLocal
    from backend.db.models import ApiUsageTracker

    today = _today_str()
    db = SessionLocal()
    try:
        row = db.query(ApiUsageTracker).order_by(ApiUsageTracker.id.desc()).first()
        if row and row.date < today:
            row.date = today
            row.call_count = 0
            row.last_updated = datetime.now(IST)
            db.commit()
            
        used = row.call_count if (row and row.date == today) else 0
        return {"date": today, "used": used, "remaining": DAILY_CALL_LIMIT - used, "limit": DAILY_CALL_LIMIT}
    finally:
        db.close()



# ═══════════════════════════════════════════════════════════════════════════
# 3. CALLABLE BUILDER — one function per endpoint
# ═══════════════════════════════════════════════════════════════════════════

def _extract_query_param_names(operation: dict) -> set[str]:
    """Extract parameter names that go in the query string."""
    names = set()
    for p in operation.get("parameters", []):
        if p.get("in") == "query":
            names.add(p["name"])
    return names


def _extract_body_param_names(operation: dict) -> set[str]:
    """
    Extract parameter names that belong in the JSON request body.
    These live at: requestBody > content > application/json > schema > properties
    CRITICAL: without this, POST endpoints like send_campaign get an empty body → 422.
    """
    try:
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        return set(schema.get("properties", {}).keys())
    except (KeyError, TypeError):
        return set()


def _build_callable(path: str, method: str, operation: dict):
    """
    Build a closure that calls this endpoint.
    Automatically separates kwargs into query params vs body params.
    """
    query_params = _extract_query_param_names(operation)
    body_params = _extract_body_param_names(operation)
    url = f"{CAMPAIGNX_BASE_URL}{path}"

    def _call(**kwargs: Any) -> dict:
        headers = {"X-API-Key": CAMPAIGNX_API_KEY}

        # Split kwargs into query vs body
        params = {k: v for k, v in kwargs.items() if k in query_params}
        body = {k: v for k, v in kwargs.items() if k in body_params}

        # Anything not recognized as query or body → guess based on method
        unrecognized = {k: v for k, v in kwargs.items() if k not in query_params and k not in body_params}
        if method.lower() == "get":
            params.update(unrecognized)
        else:
            body.update(unrecognized)

        # Make the HTTP request
        with httpx.Client(timeout=30.0) as client:
            if method.lower() == "get":
                resp = client.get(url, headers=headers, params=params)
            elif method.lower() == "post":
                resp = client.post(url, headers=headers, json=body if body else None, params=params)
            elif method.lower() == "put":
                resp = client.put(url, headers=headers, json=body if body else None, params=params)
            elif method.lower() == "delete":
                resp = client.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        # Try to parse JSON, fall back to text
        try:
            return resp.json()
        except Exception:
            return {"status_code": resp.status_code, "text": resp.text}

    # Attach metadata for introspection
    op_id = operation.get("operationId", f"{method}_{path}")
    _call.__name__ = op_id
    _call.__doc__ = operation.get("description", "")
    return _call


# ═══════════════════════════════════════════════════════════════════════════
# 4. TOOL REGISTRY — build once, use everywhere
# ═══════════════════════════════════════════════════════════════════════════

def _extract_param_schema(operation: dict) -> dict:
    """Build a combined parameter schema for logging/agent introspection."""
    schema: dict[str, Any] = {}

    # Query parameters
    for p in operation.get("parameters", []):
        if p.get("in") == "query":
            schema[p["name"]] = {
                "in": "query",
                "required": p.get("required", False),
                "type": p.get("schema", {}).get("type", "string"),
                "description": p.get("description", ""),
            }

    # Request body parameters
    try:
        body_schema = operation["requestBody"]["content"]["application/json"]["schema"]
        required_fields = set(body_schema.get("required", []))
        for name, prop in body_schema.get("properties", {}).items():
            # Handle anyOf type unions (e.g., subject can be string | null)
            prop_type = prop.get("type", "string")
            if "anyOf" in prop:
                types = [t.get("type") for t in prop["anyOf"] if t.get("type") != "null"]
                prop_type = types[0] if types else "string"
            schema[name] = {
                "in": "body",
                "required": name in required_fields,
                "type": prop_type,
                "description": prop.get("description", ""),
            }
    except (KeyError, TypeError):
        pass

    return schema


def _build_registry() -> dict[str, dict]:
    """Parse the full spec and build the tool registry. Called once."""
    global _tool_registry
    if _tool_registry:
        return _tool_registry

    spec = _fetch_and_cache_spec()
    paths = spec.get("paths", {})

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ("parameters", "summary", "description"):
                continue  # skip non-method keys

            op_id = operation.get("operationId", f"{method}_{path}")

            # Skip signup — one-time only, already done
            if op_id in SKIP_OPERATIONS:
                print(f"[api_tools] Skipping {op_id} (blocked)")
                continue

            callable_fn = _build_callable(path, method, operation)
            _tool_registry[op_id] = {
                "callable": callable_fn,
                "description": operation.get("description", operation.get("summary", "")),
                "param_schema": _extract_param_schema(operation),
                "path": path,
                "method": method.upper(),
                "operation_id": op_id,
                "tags": operation.get("tags", []),
            }
            print(f"[api_tools] Registered tool: {op_id} [{method.upper()} {path}]")

    print(f"[api_tools] Registry built — {len(_tool_registry)} tools available")
    return _tool_registry


def get_registry() -> dict[str, dict]:
    """Return the tool registry, building it if needed."""
    if not _tool_registry:
        _build_registry()
    return _tool_registry


# ═══════════════════════════════════════════════════════════════════════════
# 5. CALL TOOL BY NAME — the primary interface for agents
# ═══════════════════════════════════════════════════════════════════════════

def call_tool_by_name(tool_name: str, **kwargs) -> dict:
    """
    Call a CampaignX API tool by name.

    Resolution order:
      1. Exact operationId match
      2. Partial match — looks for tool_name as a substring of any operationId
         (e.g. "send_campaign" matches "send_campaign_api_v1_send_campaign_post")

    Budget enforcement:
      - check_budget() is called BEFORE every request
      - increment_budget() is called AFTER a successful request
    """
    registry = get_registry()

    # 1. Exact match
    tool = registry.get(tool_name)

    # 2. Partial match
    if tool is None:
        matches = [
            (op_id, entry) for op_id, entry in registry.items()
            if tool_name.lower() in op_id.lower()
        ]
        if len(matches) == 1:
            tool = matches[0][1]
        elif len(matches) > 1:
            match_names = [m[0] for m in matches]
            raise ValueError(
                f"[api_tools] Ambiguous tool name '{tool_name}'. "
                f"Matches: {match_names}. Use the full operationId."
            )
        else:
            available = list(registry.keys())
            raise ValueError(
                f"[api_tools] Unknown tool '{tool_name}'. "
                f"Available tools: {available}"
            )

    # Mock mode — return fake response without making real API call
    if MOCK_MODE:
        # Special case: report endpoint returns realistic dummy rows
        if "report" in tool["operation_id"].lower():
            import random
            bonus_clicks = random.randint(0, 10)
            bonus_opens = random.randint(0, 20)
            dummy_rows = (
                [{"EO": "Y", "EC": "Y"}] * (15 + bonus_clicks) +
                [{"EO": "Y", "EC": "N"}] * (25 + bonus_opens) +
                [{"EO": "N", "EC": "N"}] * 60
            )
            print(f"[api_tools] MOCK MODE — returning {len(dummy_rows)} dummy report rows")
            return {
                "data": dummy_rows,
                "total_rows": len(dummy_rows),
                "response_code": 200,
                "campaign_id": kwargs.get("campaign_id", "mock-123"),
            }
        print(f"[api_tools] MOCK MODE — skipping real call to {tool_name}")
        return {"campaign_id": "mock-campaign-id-1234", "response_code": 200, "message": "mock"}

    # Budget guard
    remaining = check_budget()
    print(f"[api_tools] Calling {tool['operation_id']} "
          f"({remaining} calls remaining today)")

    # Execute
    result = tool["callable"](**kwargs)

    # Track usage
    used = increment_budget()
    print(f"[api_tools] {tool['operation_id']} completed "
          f"({used}/{DAILY_CALL_LIMIT} calls used today)")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 6. TOOL DESCRIPTIONS — for frontend logs page & agent prompts
# ═══════════════════════════════════════════════════════════════════════════

def get_tool_descriptions() -> list[dict]:
    """
    Return a list of {name, method, path, description} dicts.
    Safe for serialization — no callables included.
    """
    registry = get_registry()
    return [
        {
            "name": op_id,
            "method": entry["method"],
            "path": entry["path"],
            "description": entry["description"],
        }
        for op_id, entry in registry.items()
    ]
