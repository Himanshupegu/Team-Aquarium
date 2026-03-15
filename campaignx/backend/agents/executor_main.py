import json
from backend.agents.tool_definitions import CAMPAIGNX_TOOLS, TOOL_SELECTION_PROMPT


def _discover_tool_via_llm(llm, task: str, log_callback=None) -> dict:
    """Use LLM to dynamically discover and select the appropriate API tool."""
    tool_definitions_str = json.dumps(CAMPAIGNX_TOOLS, indent=2)
    prompt = TOOL_SELECTION_PROMPT.format(
        tool_definitions=tool_definitions_str,
        task=task
    )
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)
    
    # Clean and parse JSON response
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()
    
    result = json.loads(content)
    
    if log_callback:
        log_callback(
            f"Dynamically discovered and selected tool: '{result['tool_name']}' "
            f"based on API documentation. Reasoning: {result['reasoning']}"
        )
    
    return result


# In your execute_campaigns function, replace the hardcoded send call with:

def execute_campaigns(state, llm, log_callback=None):
    succeeded = []
    failed = []

    for segment_label, variant in state.variants_to_execute.items():
        customer_ids = state.all_segments.get(segment_label, [])
        if not customer_ids:
            continue

        task = (
            f"Send an email campaign to {len(customer_ids)} customers in the "
            f"'{segment_label}' segment. The email subject is: '{variant['subject']}'. "
            f"I need to submit this campaign to the CampaignX API."
        )

        # LLM dynamically selects the tool
        try:
            tool_decision = _discover_tool_via_llm(llm, task, log_callback)
        except Exception as e:
            if log_callback:
                log_callback(f"Tool discovery failed for {segment_label}: {e}")
            failed.append(segment_label)
            continue

        # Build parameters from variant data
        params = {
            "subject": variant["subject"],
            "body": variant["body"],
            "list_customer_ids": customer_ids,
            "send_time": variant.get("send_time", state.send_time)
        }

        # Execute via api_tools.py with retry
        result = None
        for attempt in range(2):
            try:
                result = call_tool_by_name(tool_decision["tool_name"], params)
                if result and result.get("response_code") in [200, 201]:
                    succeeded.append({
                        "segment_label": segment_label,
                        "variant_label": variant["variant_label"],
                        "api_campaign_id": result.get("campaign_id"),
                        "customers_sent": len(customer_ids)
                    })
                    break
            except Exception as e:
                if attempt == 0:
                    if log_callback:
                        log_callback(f"Send attempt 1 failed for {segment_label}, retrying...")
                else:
                    if log_callback:
                        log_callback(f"Send failed after retry for {segment_label}: {e}")
                    failed.append(segment_label)

    if log_callback:
        log_callback(
            f"Executed {len(succeeded)} campaigns successfully, {len(failed)} failed"
        )

    state.execution_results = {"succeeded": succeeded, "failed": failed}
    return state