CAMPAIGNX_TOOLS = [
    {
        "name": "get_customer_cohort",
        "description": "Retrieves the full list of customers from the CampaignX API. Returns customer IDs, emails, and demographic attributes needed for targeting.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "send_campaign",
        "description": "Submits a new email marketing campaign to a targeted list of customers. The API validates that all customer IDs exist in the cohort. Use this to execute a campaign with specific content and targeting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Email subject line. Text and emojis only. Max 200 characters."
                },
                "body": {
                    "type": "string",
                    "description": "Main email body content. Supports UTF-8, emojis, and URLs. Max 5000 characters."
                },
                "list_customer_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of unique customer IDs to send the campaign to. All IDs must exist in the customer cohort."
                },
                "send_time": {
                    "type": "string",
                    "description": "Planned send time in format DD:MM:YY HH:MM:SS. Example: 15:03:26 10:30:00"
                }
            },
            "required": ["subject", "body", "list_customer_ids", "send_time"]
        }
    },
    {
        "name": "get_report",
        "description": "Fetches the performance report for a specific campaign. Returns per-customer engagement data including email opened (EO) and email clicked (EC) fields.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The unique UUID of the campaign to retrieve the report for."
                }
            },
            "required": ["campaign_id"]
        }
    }
]


TOOL_SELECTION_PROMPT = """You are an AI agent executing a marketing campaign. 
You have access to the following API tools derived from the CampaignX API documentation:

{tool_definitions}

Your current task: {task}

Based on the API documentation above, select the most appropriate tool and provide the exact parameters needed.
Respond ONLY with a JSON object in this format:
{{
    "tool_name": "<name of the tool to call>",
    "parameters": {{<parameters for the tool>}},
    "reasoning": "<one sentence explaining why you selected this tool>"
}}"""