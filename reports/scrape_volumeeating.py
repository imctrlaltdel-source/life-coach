import urllib.request, json, time, sys

def scrape_reddit(subreddit, limit=1000, sort="score"):
    results, last_created = [], None
    seen_ids = set()
    while len(results) < limit:
        params = f"subreddit={subreddit}&limit=100&sort={sort}&fields=title,selftext,url,id,score,created_utc,author,num_comments"
        if last_created:
            params += f"&before={last_created}"
        url = f"https://api.pullpush.io/reddit/search/submission/?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                posts = json.loads(r.read()).get('data', [])
            if not posts:
                print("No more posts returned, stopping.", flush=True)
                break
            new_added = 0
            for p in posts:
                pid = p.get('id')
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    results.append(p)
                    new_added += 1
            last_created = posts[-1].get('created_utc')
            print(f"Fetched batch — total {len(results)} (new {new_added}) last_ts={last_created}", flush=True)
            if new_added == 0:
                print("No new IDs in batch, stopping to prevent infinite loop.", flush=True)
                break
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}", flush=True)
            time.sleep(3)
    return results[:limit]

if __name__ == "__main__":
    print("Starting scrape of r/Volumeeating (top 1000 by score)...", flush=True)
    data = scrape_reddit("Volumeeating", limit=1000, sort="score")
    out = "/storage/emulated/0/Documents/claude/life-coach/reports/volumeeating_raw.json"
    with open(out, "w") as f:
        json.dump(data, f)
    print(f"Saved {len(data)} posts to {out}", flush=True)
