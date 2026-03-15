import sqlite3
import json

def find_best_segment():
    conn = sqlite3.connect('../campaignx.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # First, let's see the raw campaign_reports data to understand open/click values
    cursor.execute("""
        SELECT c.campaign_id, c.iteration, c.variant_label, c.segment_label, c.customer_ids,
               count(cr.id) as report_count,
               sum(case when cr.email_opened='Y' then 1 else 0 end) as opened,
               sum(case when cr.email_clicked='Y' then 1 else 0 end) as clicked
        FROM campaigns c
        LEFT JOIN campaign_reports cr ON c.campaign_id = cr.campaign_id
        GROUP BY c.campaign_id
        ORDER BY c.iteration, c.segment_label
    """)
    rows = cursor.fetchall()

    all_segments = []
    print(f"Total campaign entries: {len(rows)}\n")
    
    for row in rows:
        total = row['report_count'] or 0
        opened = row['opened'] or 0
        clicked = row['clicked'] or 0
        
        # Also count from customer_ids
        try:
            cust_ids = json.loads(row['customer_ids']) if row['customer_ids'] else []
            cust_count = len(cust_ids)
        except:
            cust_count = 0

        if total == 0:
            continue

        open_rate = opened / total
        click_rate = clicked / total
        score = (click_rate * 0.7 + open_rate * 0.3) * 100

        all_segments.append({
            'campaign_id': row['campaign_id'][:8],
            'iteration': row['iteration'],
            'variant': row['variant_label'] or '(none)',
            'segment': row['segment_label'] or '(none)',
            'sent': total,
            'cust_count': cust_count,
            'opened': opened,
            'clicked': clicked,
            'open_rate': open_rate,
            'click_rate': click_rate,
            'score': score
        })

    # Sort by score descending
    all_segments.sort(key=lambda x: x['score'], reverse=True)

    print(f"Entries with report data: {len(all_segments)}\n")
    print("=== ALL SEGMENTS RANKED BY SCORE ===\n")
    for i, seg in enumerate(all_segments, 1):
        print(f"#{i}: Score={seg['score']:.2f} | Open={seg['open_rate']:.1%} | Click={seg['click_rate']:.1%} | Sent={seg['sent']} | Custs={seg['cust_count']}")
        print(f"     Campaign={seg['campaign_id']}... | Iter={seg['iteration']} | Variant={seg['variant']} | Segment={seg['segment']}")
        print()

if __name__ == '__main__':
    find_best_segment()
