import sqlite3
import json

DB = r"d:\InXiteOut Agentic AI Hackathon\Team Aquarium\campaignx\campaignx.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Check customer_cohort table structure
print("=" * 60)
print("CUSTOMER_COHORT TABLE INFO")
print("=" * 60)
cur.execute("PRAGMA table_info(customer_cohort)")
for col in cur.fetchall():
    print(f"  {col}")

cur.execute("SELECT COUNT(*) FROM customer_cohort")
print(f"\n  Total rows: {cur.fetchone()[0]}")

cur.execute("SELECT * FROM customer_cohort LIMIT 3")
rows = cur.fetchall()
print(f"\n  Sample rows:")
for r in rows:
    print(f"    {r}")

# Check what column names exist
print("\n")
print("=" * 60)
print("CHECKING COMMON ID COLUMN NAMES")
print("=" * 60)
cur.execute("SELECT sql FROM sqlite_master WHERE name='customer_cohort'")
print(f"  CREATE statement: {cur.fetchone()}")

# Now check the live API format 
print("\n")
print("=" * 60)
print("CHECKING SEND_TIME FORMAT IN EXECUTOR")
print("=" * 60)
# Check the build_send_time function output
import sys
sys.path.insert(0, r"d:\InXiteOut Agentic AI Hackathon\Team Aquarium\campaignx")
from backend.agents.executor import build_send_time
for hour in [10, 14, 18]:
    st = build_send_time(hour)
    print(f"  build_send_time({hour}) = '{st}'")

# Check the actual API spec for send_campaign parameter expectations
print("\n")
print("=" * 60)
print("CHECKING API SPEC FOR send_campaign")
print("=" * 60)
from backend.tools.api_tools import get_registry
reg = get_registry()
for name, entry in reg.items():
    if "send_campaign" in name.lower():
        print(f"  Tool: {name}")
        print(f"  Path: {entry['path']}")
        print(f"  Method: {entry['method']}")
        print(f"  Params:")
        for pname, pinfo in entry.get("param_schema", {}).items():
            print(f"    {pname}: {pinfo}")

# Also do a quick test call to get_report for one of the API campaign IDs
print("\n")
print("=" * 60)
print("RAW API REPORT for bb52a3a9-f02f-4912-90e7-cbf8753aa15b")
print("=" * 60)
from backend.tools.api_tools import call_tool_by_name
report = call_tool_by_name("get_report", campaign_id="bb52a3a9-f02f-4912-90e7-cbf8753aa15b")
data = report.get("data", [])
print(f"  Total rows: {len(data)}")
if data:
    # Show EO/EC distribution
    eo_y = sum(1 for r in data if str(r.get("EO","")).upper() in ("Y","YES","TRUE","1"))
    ec_y = sum(1 for r in data if str(r.get("EC","")).upper() in ("Y","YES","TRUE","1"))
    print(f"  EO=Y: {eo_y}, EC=Y: {ec_y}")
    print(f"  First 3 rows: {data[:3]}")
    # Show all unique keys in the report rows
    all_keys = set()
    for r in data:
        all_keys.update(r.keys())
    print(f"  All keys in report: {all_keys}")

conn.close()
