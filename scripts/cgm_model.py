"""CGM predictive model — joins meals to the glucose peak that follows, so we can
quantify what actually drives PJ's spikes instead of describing each day in prose.

Method (deliberately simple, small-n): for each meal event, find the highest cgm
reading/peak logged within the next 5 hours, and the cgm reading closest to (but
before) the meal as baseline. delta = post-meal peak - pre-meal baseline.
Then regress delta against estimated carbs/protein/fat, and against a simple
has_protein flag, to see what actually predicts the size of the rise.

This improves every time PJ logs another day — n is small now (n=5 days as of
2026-09-06), treat early coefficients as directional, not precise, and say so.

Run: python3 scripts/cgm_model.py
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from coach_db import connect


def load_events(conn):
    meals = conn.execute(
        "SELECT id, ts, day, subtype, value_num, data_json FROM events "
        "WHERE type='meal' ORDER BY ts"
    ).fetchall()
    cgm = conn.execute(
        "SELECT ts, subtype, value_num, data_json FROM events "
        "WHERE type='cgm' AND value_num IS NOT NULL ORDER BY ts"
    ).fetchall()
    return meals, cgm


def parse_ts(ts):
    return datetime.fromisoformat(ts)


def nearest_baseline(cgm, meal_time):
    """Closest cgm reading at or before meal_time, within 3h lookback."""
    best = None
    for ts, subtype, val, dj in cgm:
        t = parse_ts(ts)
        if t <= meal_time and (meal_time - t) <= timedelta(hours=3):
            if best is None or t > parse_ts(best[0]):
                best = (ts, subtype, val, dj)
    return best


def peak_after(cgm, meal_time, window_hours=5):
    """Highest cgm value within window_hours after meal_time."""
    best = None
    for ts, subtype, val, dj in cgm:
        t = parse_ts(ts)
        if meal_time < t <= meal_time + timedelta(hours=window_hours):
            if best is None or val > best[2]:
                best = (ts, subtype, val, dj)
    return best


def main():
    conn = connect()
    meals, cgm = load_events(conn)
    conn.close()

    rows = []
    for mid, ts, day, subtype, cal, dj in meals:
        d = json.loads(dj) if dj else {}
        carbs = d.get("est_carbs_g")
        protein = d.get("est_protein_g")
        if carbs is None:
            continue  # can't model a meal with no carb estimate
        meal_time = parse_ts(ts)
        base = nearest_baseline(cgm, meal_time)
        peak = peak_after(cgm, meal_time)
        if not base or not peak:
            continue
        delta = peak[2] - base[2]
        has_protein = (protein or 0) >= 15
        rows.append({
            "day": day, "meal": subtype, "carbs_g": carbs, "protein_g": protein or 0,
            "cal": cal, "baseline": base[2], "peak": peak[2], "delta": delta,
            "has_protein_floor": has_protein, "items": d.get("items", "")[:40],
        })

    if not rows:
        print("No meals with both a carb estimate and nearby CGM data yet.")
        return

    print(f"{'day':11} {'meal':9} {'carbs':>6} {'protein':>8} {'base':>6} {'peak':>6} {'delta':>6}  items")
    for r in rows:
        print(f"{r['day']:11} {r['meal']:9} {r['carbs_g']:6.0f} {r['protein_g']:8.0f} "
              f"{r['baseline']:6.0f} {r['peak']:6.0f} {r['delta']:6.0f}  {r['items']}")

    # crude regression: delta ~ carbs_g, split by protein floor
    with_p = [r for r in rows if r["has_protein_floor"]]
    without_p = [r for r in rows if not r["has_protein_floor"]]

    def summary(group, label):
        if not group:
            return
        avg_carbs = sum(r["carbs_g"] for r in group) / len(group)
        avg_delta = sum(r["delta"] for r in group) / len(group)
        rise_per_10g = (avg_delta / avg_carbs * 10) if avg_carbs else 0
        print(f"\n{label} (n={len(group)}): avg carbs {avg_carbs:.0f}g -> avg delta +{avg_delta:.0f} mg/dL "
              f"(~{rise_per_10g:.1f} mg/dL per 10g carb)")

    print("\n--- Model (directional, small n — refines as more days come in) ---")
    summary(with_p, "Meals WITH protein floor (>=15g protein)")
    summary(without_p, "Meals WITHOUT protein floor")

    if with_p and without_p:
        wp = sum(r["delta"] for r in with_p) / len(with_p)
        np_ = sum(r["delta"] for r in without_p) / len(without_p)
        print(f"\n=> Protein floor meals rise ~{np_ - wp:.0f} mg/dL less on average than meals without it, "
              f"n={len(with_p)} vs n={len(without_p)}. Treat as directional until n is bigger.")

    print(f"\nTotal meals modeled: {len(rows)}. More days of data (still coming, per PJ's 10-day plan) will tighten this.")


if __name__ == "__main__":
    main()
