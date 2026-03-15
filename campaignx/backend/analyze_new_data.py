import sqlite3, json

def analyze_all():
    conn = sqlite3.connect('../campaignx.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT campaign_id, iteration, all_results FROM campaigns WHERE all_results IS NOT NULL ORDER BY campaign_id, iteration")
    rows = cursor.fetchall()
    
    all_variants = []
    campaigns = {}

    for row in rows:
        cid = row['campaign_id']
        it = row['iteration']
        try:
            results = json.loads(row['all_results'])
        except:
            continue
        
        if not results or not isinstance(results, list):
            continue
            
        if cid not in campaigns:
            campaigns[cid] = {}
        if it not in campaigns[cid]:
            campaigns[cid][it] = {}
            
        for r in results:
            if not isinstance(r, dict):
                continue
            seg = r.get('segment_label', '?')
            var = r.get('variant_label', '?')
            score = r.get('composite_score', 0) or 0
            open_r = r.get('open_rate', 0) or 0
            click_r = r.get('click_rate', 0) or 0
            sent = r.get('total_sent', 0)
            
            all_variants.append({
                'campaign': cid[:8], 'iteration': it, 'segment': seg, 'variant': var,
                'open_rate': open_r, 'click_rate': click_r, 'score': score, 'sent': sent
            })
            
            if seg not in campaigns[cid][it] or score > campaigns[cid][it][seg]['score']:
                campaigns[cid][it][seg] = {
                    'score': score, 'open_rate': open_r, 'click_rate': click_r, 'variant': var, 'sent': sent
                }

    # 1. TOP SEGMENTS
    all_variants.sort(key=lambda x: float(x['score'] or 0), reverse=True)
    print("=== TOP 5 BEST PERFORMING SEGMENT-VARIANTS ===\n")
    for i, v in enumerate(all_variants[:5], 1):
        print(f"#{i}: Score={v['score']:.2f} | Open={v['open_rate']:.1%} | Click={v['click_rate']:.1%} | Sent={v['sent']}")
        print(f"     Campaign={v['campaign']} | Iter={v['iteration']} | Var={v['variant']} | Seg={v['segment']}")
        print()
        
    # 2. BIGGEST RESCUES (0 to non-zero, or just biggest improvement)
    improvements = []
    for cid, iters in campaigns.items():
        sorted_iters = sorted(iters.keys())
        for i in range(len(sorted_iters) - 1):
            it1 = sorted_iters[i]
            it2 = sorted_iters[i + 1]
            for seg in iters[it1]:
                if seg in iters[it2]:
                    s1 = iters[it1][seg]
                    s2 = iters[it2][seg]
                    if s1['score'] < 10 and s2['score'] > 15: # Find rescues
                        improvements.append({
                            'campaign': cid[:8], 'segment': seg,
                            'iter_from': it1, 'iter_to': it2,
                            'score_from': s1['score'], 'score_to': s2['score'],
                            'open_from': s1['open_rate'], 'open_to': s2['open_rate'],
                            'click_from': s1['click_rate'], 'click_to': s2['click_rate']
                        })
                        
    improvements.sort(key=lambda x: x['score_to'] - x['score_from'], reverse=True)
    print("=== TOP RESCUES ===\n")
    for i, imp in enumerate(improvements[:5], 1):
        print(f"#{i}: {imp['segment']} (Iter {imp['iter_from']} -> {imp['iter_to']})")
        print(f"     Score: {imp['score_from']:.2f} -> {imp['score_to']:.2f}")
        print(f"     Open: {imp['open_from']:.1%} -> {imp['open_to']:.1%} | Click: {imp['click_from']:.1%} -> {imp['click_to']:.1%}")
        print()

if __name__ == '__main__':
    analyze_all()
