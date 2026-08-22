#!/usr/bin/env python3
"""
Reddit scraper using Pullpush.io API (no auth required).
Usage:
    python3 scrape_reddit.py --subreddit Volumeeating --limit 1000 --sort score
    python3 scrape_reddit.py --subreddit Volumeeating --query "vegetarian" --limit 100
"""
import urllib.request, json, time, argparse, sys

BASE = "https://api.pullpush.io/reddit/search/submission/"

def scrape(subreddit, limit=100, query=None, sort="score", fields=None, after=None, before=None):
    results = []
    batch = 100
    fetched = 0
    last_created = None

    if fields is None:
        fields = "title,selftext,url,id,score,created_utc,author,num_comments"

    while fetched < limit:
        params = f"subreddit={subreddit}&limit={min(batch, limit-fetched)}&sort={sort}&fields={fields}"
        if query:
            params += f"&q={urllib.parse.quote(query)}"
        if last_created:
            params += f"&before={last_created}"
        if after:
            params += f"&after={after}"

        url = f"{BASE}?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                posts = data.get('data', [])
                if not posts:
                    break
                results.extend(posts)
                fetched += len(posts)
                last_created = posts[-1].get('created_utc')
                print(f"  Fetched {fetched}/{limit}...", end='\r', file=sys.stderr)
                if len(posts) < batch:
                    break
                time.sleep(1)  # rate limit
        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            time.sleep(3)
            break

    return results

def get_comments(post_id, limit=50):
    url = f"https://api.pullpush.io/reddit/search/comment/?link_id={post_id}&limit={limit}&sort=score"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
            return data.get('data', [])
    except:
        return []

if __name__ == "__main__":
    import urllib.parse
    parser = argparse.ArgumentParser()
    parser.add_argument("--subreddit", default="Volumeeating")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--query", default=None)
    parser.add_argument("--sort", default="score")
    parser.add_argument("--output", default="scraped.json")
    args = parser.parse_args()

    print(f"Scraping r/{args.subreddit} (limit={args.limit}, sort={args.sort})...", file=sys.stderr)
    posts = scrape(args.subreddit, args.limit, args.query, args.sort)
    print(f"\nTotal: {len(posts)} posts", file=sys.stderr)

    with open(args.output, 'w') as f:
        json.dump(posts, f, indent=2)
    print(f"Saved to {args.output}", file=sys.stderr)
