import sqlite3, json

conn = sqlite3.connect('../campaignx.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get detail for campaign d9077717
cursor.execute("SELECT campaign_id, iteration, all_results FROM campaigns WHERE campaign_id LIKE 'd9077717%' AND all_results IS NOT NULL ORDER BY iteration")
for row in cursor.fetchall():
    results = json.loads(row['all_results'])
    print(f'Iter {row["iteration"]}: {len(results)} entries')
    for r in results:
        seg = r.get('segment_label', '?')
        var = r.get('variant_label', '?')
        op = r.get('open_rate', 0)
        cl = r.get('click_rate', 0)
        sc = r.get('composite_score', 0)
        sent = r.get('total_sent', 0)
        print(f'  {var} {seg}: Open={op:.1%} Click={cl:.1%} Score={sc:.2f} Sent={sent}')

print("\n--- Also check campaign 9796c77a ---")
cursor.execute("SELECT campaign_id, iteration, all_results FROM campaigns WHERE campaign_id LIKE '9796c77a%' AND all_results IS NOT NULL ORDER BY iteration")
for row in cursor.fetchall():
    results = json.loads(row['all_results'])
    print(f'Iter {row["iteration"]}: {len(results)} entries')
    for r in results:
        seg = r.get('segment_label', '?')
        var = r.get('variant_label', '?')
        op = r.get('open_rate', 0)
        cl = r.get('click_rate', 0)
        sc = r.get('composite_score', 0)
        sent = r.get('total_sent', 0)
        print(f'  {var} {seg}: Open={op:.1%} Click={cl:.1%} Score={sc:.2f} Sent={sent}')
