#!/usr/bin/env python3
"""
meal.py — Meal logging and calorie tracking for Prateek Jain (PJ)
37-year-old diabetic in Bangalore. Run from Termux terminal.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: load .env before anything else
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).parent / ".env"
LOG_DIR = Path(__file__).parent / "logs" / "diet"

def _load_env():
    """Read ANTHROPIC_API_KEY from .env file."""
    if not ENV_PATH.exists():
        ENV_PATH.write_text("ANTHROPIC_API_KEY=your-key-here\n")
        print(f"[setup] Created template .env at {ENV_PATH}")
        print("        Please add your Anthropic API key and re-run.")
        sys.exit(0)
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL          = "claude-haiku-4-5"          # fast & cheap for calorie lookup
TODAY          = date.today().isoformat()    # "YYYY-MM-DD"
TARGET_KCAL    = 1200                        # dietician target intake
BMR            = 1631                        # PJ's BMR — device-measured Apr 25, 2026
TDEE_15K       = 2120                        # TDEE at gym+walking day (no run)
CAL_PER_1K     = 40                          # calories burned per 1 000 steps (80 kg)
PROTEIN_WARN   = 80                          # g/day — kidney ceiling warning
PROTEIN_HARD   = 90                          # g/day — hard limit warning

# Correction factors (PJ's rule):
# Home food: +20% | Restaurant food: +30%
CORRECTION_HOME       = 1.20
CORRECTION_RESTAURANT = 1.30

# High-GI foods that need flagging for a diabetic
HIGH_GI_KEYWORDS = [
    "white rice", "maida", "sugar", "fruit juice", "chips",
    "nippattu", "biscuit", "cake", "bread", "naan", "parotta",
    "soft drink", "cola", "soda", "candy", "sweets",
]

# Stable system prompt — cached on first call, reused across all calls
SYSTEM_PROMPT = """You are a brutally accurate clinical dietitian for Prateek Jain, a
37-year-old diabetic man in Bangalore, India. Your job: find the REAL calories, not
comfortable estimates. Research shows people underestimate calories by 30-50%.
Your estimates must skew HIGH, not low.

CRITICAL RULES FOR ACCURACY:
1. Indian home cooking uses 1-3 tbsp oil per dish (120-360 hidden calories) — ALWAYS add this
2. Portions described verbally are almost always LARGER than stated — assume 20-30% more
3. "Small" bowl in India = 250-300ml. "Medium" = 400ml. Never go below these.
4. Pav = 50-60g each (not 30g). Roti = 35-40g. Paratha = 60-80g with 1 tsp ghee minimum.
5. Restaurant/cafe food: add 30% on top of home-cooked estimates (hidden butter, oil, sugar)
6. Whey shake: 30g scoop = 120 cal, 25g protein — always exact, never estimate lower
7. Buddha bowl at restaurant: dressing alone = 100-150 cal hidden
8. If something sounds too low, it is. Be the skeptic.

Plate rule (dietician guideline):
- 50% non-starchy vegetables (eaten FIRST)
- 25% protein (dal, egg, chicken, paneer, curd, legumes)
- 25% complex carbs (roti, oats — flag white rice >100g)

High-GI items to flag: white rice (>100g), maida, sugar, fruit juice, chips,
biscuits, cakes, white bread, naan, parotta, soft drinks, sweets.

Kidney constraint: protein must stay below 90g/day (warn at 80g).

Return ONLY valid JSON. No prose, no markdown. Exactly these keys:
{
  "calories": <int>,
  "protein_g": <float>,
  "carbs_g": <float>,
  "fat_g": <float>,
  "hidden_calories_note": "<str — explain what hidden calories you added and why>",
  "confidence": "<high|medium|low>",
  "high_gi_items": [<str>, ...],
  "plate_rule_pass": <bool>,
  "plate_rule_notes": "<str>"
}"""

# ---------------------------------------------------------------------------
# JSON log helpers
# ---------------------------------------------------------------------------

def _log_path() -> Path:
    return LOG_DIR / f"{TODAY}.json"


def _load_log() -> dict:
    p = _log_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"date": TODAY, "meals": [], "total_calories": 0,
            "total_protein": 0.0, "steps": 0}


def _save_log(data: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _log_path().write_text(json.dumps(data, indent=2))


def _recalc_totals(data: dict) -> dict:
    data["total_calories"] = sum(m["calories"] for m in data["meals"])
    data["total_protein"]  = round(sum(m["protein_g"] for m in data["meals"]), 1)
    return data

# ---------------------------------------------------------------------------
# Claude API call (with prompt caching on the system prompt)
# ---------------------------------------------------------------------------

def _call_claude(user_message: str) -> dict:
    """Call Claude API via raw HTTP — no SDK dependency."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-key-here":
        print("[error] ANTHROPIC_API_KEY not set in .env")
        return {}

    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 512,
        "system": [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [{"role": "user", "content": user_message}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
            "content-type": "application/json",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = data["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        print(f"[error] API HTTP {e.code}: {e.read().decode()}")
        return {}
    except Exception as e:
        print(f"[error] {e}")
        return {}

    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"\n[error] Could not parse response:\n{raw}")
        return {}

# ---------------------------------------------------------------------------
# Risk / warning helpers
# ---------------------------------------------------------------------------

def _gi_warning(high_gi_items: list[str]) -> str | None:
    if not high_gi_items:
        return None
    items = ", ".join(high_gi_items)
    return (f"  ⚠  HbA1c RISK: High-GI items detected — {items}\n"
            "     These spike blood glucose. Eat less, swap, or pair with fibre.")


def _protein_warning(total_protein: float) -> str | None:
    if total_protein >= PROTEIN_HARD:
        return (f"  🚨 KIDNEY ALERT: Daily protein {total_protein:.1f} g exceeds "
                f"hard limit of {PROTEIN_HARD} g!\n"
                "     Stop adding protein-rich foods today.")
    if total_protein >= PROTEIN_WARN:
        return (f"  ⚠  Protein nearing kidney ceiling: {total_protein:.1f} g "
                f"(warn at {PROTEIN_WARN} g, hard limit {PROTEIN_HARD} g).\n"
                "     Be cautious with remaining meals.")
    return None


def _deficit_info(log: dict) -> dict:
    """Return deficit statistics for today."""
    eaten      = log["total_calories"]
    steps      = log.get("steps", 0)
    step_burn  = round((steps / 1000) * CAL_PER_1K)
    net_intake = eaten - step_burn                  # effective intake after steps
    # Deficit vs TDEE (what the body actually needs today)
    tdee_today = BMR + step_burn                    # simplified: BMR + activity
    deficit    = tdee_today - net_intake
    on_track   = deficit >= 500                     # 500 kcal/day → ~3500/week → ~0.5 kg
    return {
        "eaten":      eaten,
        "steps":      steps,
        "step_burn":  step_burn,
        "net_intake": net_intake,
        "tdee_today": tdee_today,
        "deficit":    deficit,
        "on_track":   on_track,
    }

# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def action_log_meal():
    print("\n--- Log a Meal ---")
    desc = input("Describe what you ate (e.g. 'dal chawal, small bowl of curd, salad'): ").strip()
    if not desc:
        print("Nothing entered.")
        return

    meal_time = input("Meal time label (e.g. breakfast / lunch / snack / dinner) [meal]: ").strip()
    if not meal_time:
        meal_time = "meal"

    location = input("Home or restaurant? [home]: ").strip().lower()
    correction = CORRECTION_RESTAURANT if location == "restaurant" else CORRECTION_HOME

    print("  Asking Claude for nutrition estimate…")
    prompt = (
        f"Analyse this meal for Prateek: {desc}\n\n"
        "Be a skeptic. Assume portions are larger than described. Add hidden oil/butter/ghee "
        "for all Indian home cooking. For restaurant food add 30% on top. "
        "Never underestimate. Return JSON as instructed."
    )
    nutrition = _call_claude(prompt)
    if not nutrition:
        return

    log  = _load_log()
    raw_cal = int(nutrition.get("calories", 0))
    corrected_cal = round(raw_cal * correction)
    correction_pct = int((correction - 1) * 100)

    meal = {
        "time":                 meal_time,
        "description":          desc,
        "calories":             corrected_cal,
        "calories_raw":         raw_cal,
        "protein_g":            float(nutrition.get("protein_g", 0)),
        "carbs_g":              float(nutrition.get("carbs_g", 0)),
        "fat_g":                float(nutrition.get("fat_g", 0)),
        "hidden_calories_note": nutrition.get("hidden_calories_note", ""),
        "confidence":           nutrition.get("confidence", "medium"),
        "high_gi_items":        nutrition.get("high_gi_items", []),
        "plate_rule_pass":      nutrition.get("plate_rule_pass", False),
        "plate_rule_notes":     nutrition.get("plate_rule_notes", ""),
    }
    log["meals"].append(meal)
    log = _recalc_totals(log)
    _save_log(log)

    # ---- Display result ----
    print(f"\n  {meal_time.capitalize()}: {desc}")
    print(f"  Calories  : {corrected_cal} kcal  (AI estimate: {raw_cal}, +{correction_pct}% correction applied)")
    print(f"  Protein   : {meal['protein_g']} g  |  "
          f"Carbs: {meal['carbs_g']} g  |  "
          f"Fat: {meal['fat_g']} g")
    print(f"  Confidence: {meal['confidence']}")
    if meal["hidden_calories_note"]:
        print(f"  Hidden cal: {meal['hidden_calories_note']}")

    plate_ok = "✓ PASS" if meal["plate_rule_pass"] else "✗ FAIL"
    print(f"  Plate rule: {plate_ok} — {meal['plate_rule_notes']}")

    gi_warn = _gi_warning(meal["high_gi_items"])
    if gi_warn:
        print(gi_warn)

    # Running daily total
    print(f"\n  Daily total so far: {log['total_calories']} / {TARGET_KCAL} kcal target")
    remaining = TARGET_KCAL - log["total_calories"]
    if remaining > 0:
        print(f"  Remaining budget  : {remaining} kcal")
    else:
        print(f"  ⚠  Over target by {abs(remaining)} kcal")

    prot_warn = _protein_warning(log["total_protein"])
    if prot_warn:
        print(prot_warn)


def action_check_deficit():
    print("\n--- Today's Deficit Check ---")
    log  = _load_log()
    info = _deficit_info(log)

    print(f"  Calories eaten    : {info['eaten']} kcal")
    print(f"  Steps walked      : {info['steps']:,}")
    print(f"  Calories burned   : {info['step_burn']} kcal  "
          f"({info['steps']:,} steps × {CAL_PER_1K} kcal/1k)")
    print(f"  Net intake        : {info['net_intake']} kcal")
    print(f"  Est. TDEE today   : {info['tdee_today']} kcal  (BMR {BMR} + activity)")
    print(f"  Deficit           : {info['deficit']} kcal")

    if info["on_track"]:
        print("  ✓ ON TRACK for 0.5 kg/week loss  (need ≥500 kcal deficit/day)")
    else:
        needed = 500 - info["deficit"]
        print(f"  ✗ NOT on track. Need {needed} more kcal deficit "
              f"(eat {needed} less or walk ~{round(needed/CAL_PER_1K)*1000:,} more steps).")

    prot_warn = _protein_warning(log.get("total_protein", 0))
    if prot_warn:
        print(prot_warn)


def action_steps_offset():
    print("\n--- Steps Offset Calculator ---")
    try:
        steps_input = input("Enter total steps walked today: ").strip().replace(",", "")
        steps = int(steps_input)
    except ValueError:
        print("Invalid number.")
        return

    log = _load_log()
    log["steps"] = steps
    _save_log(log)

    burned = round((steps / 1000) * CAL_PER_1K)
    info   = _deficit_info(log)

    print(f"\n  Steps entered     : {steps:,}")
    print(f"  Calories burned   : {burned} kcal")
    print(f"  Calories eaten    : {log['total_calories']} kcal")
    print(f"  Net intake        : {info['net_intake']} kcal")
    print(f"  Deficit vs TDEE   : {info['deficit']} kcal")

    if info["on_track"]:
        print("  ✓ ON TRACK for 0.5 kg/week loss")
    else:
        needed = 500 - info["deficit"]
        print(f"  ✗ Need {needed} more kcal deficit today.")


def action_view_log():
    print(f"\n--- Today's Log ({TODAY}) ---")
    log = _load_log()

    if not log["meals"]:
        print("  No meals logged yet.")
        return

    for i, m in enumerate(log["meals"], 1):
        plate_ok = "✓" if m.get("plate_rule_pass") else "✗"
        gi_tag   = "⚠ HI-GI" if m.get("high_gi_items") else ""
        print(f"\n  {i}. [{m['time']}] {m['description']}")
        print(f"     {m['calories']} kcal  |  "
              f"P:{m['protein_g']}g  C:{m['carbs_g']}g  F:{m['fat_g']}g  "
              f"| Plate {plate_ok}  {gi_tag}")
        if m.get("high_gi_items"):
            print(f"     High-GI: {', '.join(m['high_gi_items'])}")
        if m.get("plate_rule_notes"):
            print(f"     Notes: {m['plate_rule_notes']}")

    print(f"\n  ─────────────────────────────────────────")
    print(f"  Total  : {log['total_calories']} kcal  |  "
          f"Protein: {log['total_protein']} g")
    print(f"  Steps  : {log.get('steps', 0):,}  |  "
          f"Target : {TARGET_KCAL} kcal")

    prot_warn = _protein_warning(log.get("total_protein", 0))
    if prot_warn:
        print(prot_warn)


def action_plate_check():
    print("\n--- Quick Plate Check ---")
    desc = input("Describe the meal you're about to eat: ").strip()
    if not desc:
        return

    print("  Checking plate rule…")
    prompt = (
        f"Check this meal against the plate rule for Prateek: {desc}\n\n"
        "Focus ONLY on whether it follows 50% veg / 25% protein / 25% carbs, "
        "and whether vegetables should be eaten first. "
        "Return JSON as instructed."
    )
    nutrition = _call_claude(prompt)
    if not nutrition:
        return

    plate_ok = "✓ PASS" if nutrition.get("plate_rule_pass") else "✗ FAIL"
    print(f"\n  Plate rule: {plate_ok}")
    print(f"  Notes     : {nutrition.get('plate_rule_notes', '')}")

    gi_warn = _gi_warning(nutrition.get("high_gi_items", []))
    if gi_warn:
        print(gi_warn)

    # Show rough estimates too
    print(f"\n  Est. calories : {nutrition.get('calories', '?')} kcal")
    print(f"  Est. protein  : {nutrition.get('protein_g', '?')} g  |  "
          f"Carbs: {nutrition.get('carbs_g', '?')} g  |  "
          f"Fat: {nutrition.get('fat_g', '?')} g")

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

MENU = """
╔══════════════════════════════════════════╗
║   PJ's Meal Tracker  ({date})   ║
╠══════════════════════════════════════════╣
║  1. Log a meal                           ║
║  2. Check today's deficit                ║
║  3. Steps offset calculator              ║
║  4. View today's log                     ║
║  5. Quick plate check                    ║
║  0. Exit                                 ║
╚══════════════════════════════════════════╝
"""

ACTIONS = {
    "1": action_log_meal,
    "2": action_check_deficit,
    "3": action_steps_offset,
    "4": action_view_log,
    "5": action_plate_check,
}


def main():
    # Ensure log directory exists on first run
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your-key-here":
        print(f"\n[error] ANTHROPIC_API_KEY not set in {ENV_PATH}")
        print("        Edit the file and add your key, then re-run.")
        sys.exit(1)

    print(MENU.format(date=TODAY))

    while True:
        try:
            choice = input("\nChoice [0-5]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if choice == "0":
            print("Bye!")
            break
        elif choice in ACTIONS:
            try:
                ACTIONS[choice]()
            except anthropic.AuthenticationError:
                print("\n[error] Invalid API key. Check your .env file.")
            except anthropic.RateLimitError:
                print("\n[error] Rate limited. Wait a moment and try again.")
            except anthropic.APIStatusError as e:
                print(f"\n[error] API error {e.status_code}: {e.message}")
            except anthropic.APIConnectionError:
                print("\n[error] Network error. Check your internet connection.")
        else:
            print("  Please enter 0–5.")


if __name__ == "__main__":
    main()
