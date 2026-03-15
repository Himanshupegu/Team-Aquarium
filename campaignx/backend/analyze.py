import sqlite3

def analyze_results():
    conn = sqlite3.connect('../campaignx.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all campaigns with their iteration and segment
    cursor.execute("SELECT campaign_id, iteration, segment_label FROM campaigns")
    campaigns = cursor.fetchall()
    
    print("\n--- CAMPAIGN METRICS BY ITERATION ---")
    metrics_by_iter = {}
    
    for camp in campaigns:
        c_id = camp['campaign_id']
        it = camp['iteration']
        seg = camp['segment_label']
        
        if it is None:
            continue
            
        if it not in metrics_by_iter:
            metrics_by_iter[it] = []
            
        cursor.execute("SELECT count(*) as total, sum(case when email_opened='Y' then 1 else 0 end) as opened, sum(case when email_clicked='Y' then 1 else 0 end) as clicked FROM campaign_reports WHERE campaign_id=?", (c_id,))
        rep = cursor.fetchone()
        
        total = rep['total'] or 0
        opened = rep['opened'] or 0
        clicked = rep['clicked'] or 0
        
        if total > 0:
            metrics_by_iter[it].append({
                'segment': seg,
                'sent': total,
                'opened': opened,
                'clicked': clicked,
                'open_rate': opened / total,
                'click_rate': clicked / total,
                'score': ((clicked / total) * 0.7 + (opened / total) * 0.3) * 100
            })

    for it in sorted(metrics_by_iter.keys()):
        print(f"\nIteration {it}:")
        segs = metrics_by_iter[it]
        total_sent = sum(s['sent'] for s in segs)
        total_opened = sum(s['opened'] for s in segs)
        total_clicked = sum(s['clicked'] for s in segs)
        avg_open = total_opened / total_sent if total_sent else 0
        avg_click = total_clicked / total_sent if total_sent else 0
        avg_score = (avg_click * 0.7 + avg_open * 0.3) * 100
        
        print(f"  Overall Sent: {total_sent}, Open Rate: {avg_open:.1%}, Click Rate: {avg_click:.1%}, Score: {avg_score:.1f}")
        
        if segs:
            best_seg = max(segs, key=lambda x: x['score'])
            print(f"  Best Segment: {best_seg['segment']} (Score: {best_seg['score']:.1f}, Open: {best_seg['open_rate']:.1%}, Click: {best_seg['click_rate']:.1%})")

if __name__ == '__main__':
    analyze_results()
