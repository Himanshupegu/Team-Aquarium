import sqlite3
import json

def main():
    conn = sqlite3.connect('campaignx.db')
    cursor = conn.cursor()
    
    query = """
    SELECT 
        c.iteration,
        c.segment_label,
        COUNT(r.id) as emails_sent,
        SUM(CASE WHEN r.email_opened = 'Y' THEN 1 ELSE 0 END) as emails_opened,
        SUM(CASE WHEN r.email_clicked = 'Y' THEN 1 ELSE 0 END) as emails_clicked
    FROM campaigns c
    JOIN campaign_reports r ON c.campaign_id = r.campaign_id
    GROUP BY c.iteration, c.segment_label
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    insights = []
    
    for r in rows:
        iteration = r[0]
        segment = r[1]
        sent = r[2]
        opened = r[3]
        clicked = r[4]
        
        open_rate = (opened / sent * 100) if sent > 0 else 0
        click_rate = (clicked / sent * 100) if sent > 0 else 0
        
        insights.append({
            "iteration": iteration,
            "segment": segment,
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "open_rate_pct": round(open_rate, 2),
            "click_rate_pct": round(click_rate, 2)
        })
        
    with open('metrics.json', 'w') as f:
        json.dump(insights, f, indent=2)

    conn.close()

if __name__ == "__main__":
    main()
