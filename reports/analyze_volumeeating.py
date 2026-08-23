import json, re
from pathlib import Path
from collections import defaultdict

REPORTS_DIR = Path(__file__).resolve().parent

with open(REPORTS_DIR / "volumeeating_raw.json") as f:
    posts = json.load(f)

print(f"Total posts loaded: {len(posts)}")

# EXCLUDE keywords — meat, fish etc.
EXCLUDE = [
    r"\bbeef\b", r"\bchicken\b", r"\bpork\b", r"\bturkey\b", r"\btuna\b",
    r"\bsalmon\b", r"\bshrimp\b", r"\bbacon\b", r"\bground meat\b",
    r"\bground beef\b", r"\bdeli\b", r"\bpepperoni\b", r"\bsausage\b",
    r"\bham\b", r"\bcarnitas\b", r"\bmeatball", r"\bmeatloaf\b",
    r"\bsteak\b", r"\bcod\b", r"\btilapia\b", r"\bcrab\b", r"\blobster\b",
    r"\bveal\b", r"\blamb\b", r"\bmutton\b", r"\banchov", r"\bsardine",
    r"\bprawn", r"\bcalamari\b", r"\bsquid\b", r"\bmussel", r"\bclam\b",
    r"\bscallop", r"\balcohol\b", r"\bwine\b", r"\bbeer\b",
    r"\bprotein bar\b", r"\bquest bar\b",
    r"\bmince\b", r"\bmeat sauce\b", r"\bbrisket\b", r"\bribs\b",
    r"\bwing\b", r"\bnugget\b", r"\bpatty\b", r"\bbolognese\b",
    r"\bcarne\b", r"\bpollo\b",
]

# INCLUDE keywords — vegetarian volume eating
INCLUDE = [
    "vegetarian", "vegan", "tofu", "paneer", "cottage cheese",
    "egg white", "greek yogurt", "yogurt", "yoghurt", "curd",
    "broccoli", "cauliflower", "zucchini", "mushroom", "spinach",
    "lentil", "dal", "bean", "pea", "peas", "squash", "cucumber",
    "low carb", "high protein", "fiber", "volume", "filling",
    "soup", "salad", "veggie", "vegetable", "veg ",
    "kale", "chickpea", "eggplant", "aubergine", "asparagus",
    "cabbage", "bell pepper", "brussels", "kimchi", "edamame",
    "seitan", "tempeh", "quinoa", "oat", "chia",
    "smoothie", "bowl", "wrap", "curry", "stir fry", "stir-fry",
    "casserole", "stew", "chili", "chilli",
    "burrito bowl", "buddha bowl", "poke", "omelet", "omelette",
    "frittata", "scramble", "pancake", "shirataki", "konjac",
]

def has_meat(text):
    for pat in EXCLUDE:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False

def has_include(text):
    t = text.lower()
    for kw in INCLUDE:
        if kw in t:
            return True
    return False

def extract_macros(text):
    """Extract calories/carbs/protein/fat if mentioned in the post text."""
    macros = {}
    # Calories
    m = re.search(r"(\d{2,4})\s*(?:cal|kcal|calorie)", text, re.IGNORECASE)
    if m:
        macros["cal"] = int(m.group(1))
    # Protein
    m = re.search(r"(\d{1,3})\s*g?\s*(?:of\s+)?protein", text, re.IGNORECASE)
    if m:
        macros["protein"] = int(m.group(1))
    # Carbs
    m = re.search(r"(\d{1,3})\s*g?\s*(?:of\s+)?(?:carb|carbohydrate)", text, re.IGNORECASE)
    if m:
        macros["carbs"] = int(m.group(1))
    # Fat
    m = re.search(r"(\d{1,3})\s*g?\s*(?:of\s+)?fat", text, re.IGNORECASE)
    if m:
        macros["fat"] = int(m.group(1))
    # Fiber
    m = re.search(r"(\d{1,3})\s*g?\s*(?:of\s+)?fib(?:er|re)", text, re.IGNORECASE)
    if m:
        macros["fiber"] = int(m.group(1))
    return macros

def categorize(text):
    t = text.lower()
    cats = []
    if any(w in t for w in ["soup", "broth", "stew", "chili", "chilli", "ramen", "pho"]):
        cats.append("Soups & Broths")
    if any(w in t for w in ["tofu", "paneer", "tempeh", "seitan"]):
        cats.append("Tofu & Paneer Dishes")
    if any(w in t for w in ["egg white", "omelet", "omelette", "frittata", "scramble", "egg bite"]):
        cats.append("Egg-Based Meals")
    if any(w in t for w in ["salad", "raw", "slaw"]):
        cats.append("Salads & Raw Volume")
    if any(w in t for w in ["curry", "dal", "paneer", "roti", "dosa", "sambar", "sambhar", "chana", "bhindi", "masala", "sabzi", "sabji", "tikka", "biryani", "poha", "upma", "idli"]):
        cats.append("Low-Carb Indian Adaptations")
    if any(w in t for w in ["snack", "chip", "cracker", "dip", "bar"]):
        cats.append("Snacks & Between-Meal Fillers")
    if any(w in t for w in ["breakfast", "oat", "pancake", "waffle", "smoothie", "yogurt bowl", "yoghurt bowl", "chia pudding"]):
        cats.append("Breakfast Options")
    if any(w in t for w in ["meal prep", "batch", "week of", "prep for", "planned"]):
        cats.append("Meal Prep / Batch Cook")
    return cats

def satiety_rating(text, macros):
    """Rough satiety heuristic — protein + fiber + volume mentions."""
    t = text.lower()
    score = 0
    if macros.get("protein", 0) >= 25: score += 2
    elif macros.get("protein", 0) >= 15: score += 1
    if macros.get("fiber", 0) >= 10: score += 2
    elif macros.get("fiber", 0) >= 5: score += 1
    for w in ["filling", "full", "satiety", "satisfying", "huge", "massive", "volume", "big bowl", "giant"]:
        if w in t:
            score += 1
    for w in ["soup", "broth", "cucumber", "zucchini", "cauliflower", "broccoli", "cabbage", "spinach", "salad"]:
        if w in t:
            score += 1
    if score >= 5: return "HIGH"
    if score >= 2: return "MEDIUM"
    return "LOW"

def india_adaptability(text):
    t = text.lower()
    hard = ["shirataki", "konjac", "seitan", "tempeh", "kombucha", "kelp", "nutritional yeast",
            "liquid aminos", "coconut aminos", "cottage cheese", "skyr", "kefir",
            "quest", "halo top", "chomps", "oikos", "fage", "chobani",
            "walden farms", "beyond", "impossible", "just egg",
            "trader joe", "aldi", "costco", "kirkland", "kodiak"]
    easy = ["paneer", "dal", "roti", "dosa", "sambhar", "chana", "curd", "dahi", "yogurt", "yoghurt",
            "cucumber", "tomato", "onion", "spinach", "cauliflower", "cabbage", "carrot",
            "egg white", "tofu", "mushroom", "chickpea", "moong", "rajma"]
    hard_count = sum(1 for w in hard if w in t)
    easy_count = sum(1 for w in easy if w in t)
    if hard_count >= 2: return "LOW"
    if hard_count >= 1 and easy_count == 0: return "LOW"
    if easy_count >= 2: return "HIGH"
    if easy_count >= 1: return "HIGH"
    return "MEDIUM"

qualifying = []
excluded_meat = 0
excluded_no_include = 0

for p in posts:
    title = p.get("title", "") or ""
    body = p.get("selftext", "") or ""
    full = f"{title} {body}"
    if has_meat(full):
        excluded_meat += 1
        continue
    if not has_include(full) and len(body) < 20:
        # skip picture-only posts w/ no keyword match
        excluded_no_include += 1
        continue
    if not has_include(full):
        excluded_no_include += 1
        continue
    macros = extract_macros(full)
    cats = categorize(full)
    if not cats:
        cats = ["Uncategorized"]
    sat = satiety_rating(full, macros)
    ind = india_adaptability(full)
    qualifying.append({
        "id": p.get("id"),
        "title": title,
        "body": body[:500],
        "score": p.get("score", 0),
        "num_comments": p.get("num_comments", 0),
        "url": p.get("url", ""),
        "author": p.get("author", ""),
        "created_utc": p.get("created_utc"),
        "macros": macros,
        "categories": cats,
        "satiety": sat,
        "india_adaptability": ind,
    })

print(f"Excluded (meat/fish/etc): {excluded_meat}")
print(f"Excluded (no include keyword): {excluded_no_include}")
print(f"Qualifying: {len(qualifying)}")

# Sort qualifying by score
qualifying.sort(key=lambda x: -x["score"])

# Category counts
cat_counts = defaultdict(int)
for q in qualifying:
    for c in q["categories"]:
        cat_counts[c] += 1
print("\nCategory counts:")
for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}")

# Save filtered
with open(REPORTS_DIR / "volumeeating_qualifying.json", "w") as f:
    json.dump(qualifying, f, indent=2)

# Print top 30 titles for inspection
print("\n=== TOP 30 QUALIFYING POSTS ===")
for i, q in enumerate(qualifying[:30]):
    print(f"{i+1}. [{q['score']}] {q['title'][:100]}")
    print(f"   cats={q['categories']} sat={q['satiety']} india={q['india_adaptability']} macros={q['macros']}")
