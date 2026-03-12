import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, r"d:\InXiteOut Agentic AI Hackathon\Team Aquarium\campaignx")
from backend.tools.api_tools import call_tool_by_name
import time

def test_api():
    cta_url = "https://superbfsi.com/xdeposit/explore/"
    customers = ["CUST0001", "CUST0002"]
    
    # 1. Plain text with URL
    body1 = f"Hello. Claim your reward: {cta_url}"
    print("Sending Variant 1 (Plain text)")
    res1 = call_tool_by_name("send_campaign", subject="Test 1", body=body1, list_customer_ids=customers, send_time="01:01:26 12:00:00")
    print("Res1:", res1)
    
    # 2. HTML link
    body2 = f"Hello. <a href='{cta_url}'>Claim your reward</a>"
    print("Sending Variant 2 (HTML A tag)")
    res2 = call_tool_by_name("send_campaign", subject="Test 2", body=body2, list_customer_ids=customers, send_time="01:01:26 12:00:00")
    print("Res2:", res2)
    
    # 3. Full HTML doc
    body3 = f"<html><body>Hello. <a href='{cta_url}'>Claim your reward</a></body></html>"
    print("Sending Variant 3 (Full HTML)")
    res3 = call_tool_by_name("send_campaign", subject="Test 3", body=body3, list_customer_ids=customers, send_time="01:01:26 12:00:00")
    print("Res3:", res3)

    time.sleep(2) # wait for mock processing

    for i, res in enumerate([res1, res2, res3]):
        cid = res.get("campaign_id")
        if cid:
            rep = call_tool_by_name("get_report", campaign_id=cid)
            print(f"Report {i+1}:", rep.get("data"))

if __name__ == "__main__":
    test_api()
