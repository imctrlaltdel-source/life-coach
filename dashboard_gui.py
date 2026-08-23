#!/usr/bin/env python3
"""
PJ's Life Coach — Native Android GUI Dashboard
Run: python3 dashboard_gui.py
Requires: Termux:GUI app installed and running
"""

import termuxgui as tg
import json
from datetime import date, timedelta
from pathlib import Path

BASE = Path("/storage/emulated/0/Documents/claude/life-coach")
INDEX_FILE = BASE / "logs/index.json"
TODAY = date.today()

# ── Data ─────────────────────────────────────────────────────────────────────

BODY_COMP = {"date": "2026-04-25", "weight": 80.25, "bf": 23.7, "muscle": 55.1, "vf": 13, "bmr": 1631}
WEIGHT_GOAL = 76.0
VF_GOAL = 10
WEEKLY_TARGET = 7000
BMR = 1631

DAILY_DATA = {
    "04-21": {"eaten": 1400, "tdee": 2151, "gym": None, "run": None,  "kriya": True,  "weed_clean": None,  "parents": None,  "steps": 13.0},
    "04-22": {"eaten": 1330, "tdee": 2451, "gym": True, "run": False, "kriya": True,  "weed_clean": None,  "parents": True,  "steps": 13.0},
    "04-23": {"eaten": 1640, "tdee": 2161, "gym": False,"run": False, "kriya": None,  "weed_clean": None,  "parents": None,  "steps": 13.3},
    "04-24": {"eaten": 1330, "tdee": 2451, "gym": True, "run": False, "kriya": True,  "weed_clean": True,  "parents": None,  "steps": 13.0},
    "04-25": {"eaten": 760,  "tdee": 2646, "gym": False,"run": True,  "kriya": True,  "weed_clean": True,  "parents": None,  "steps": 11.0},
}

RUNS = [
    ("04-12", 5.20, "—",  "—"),
    ("04-14", 5.21, "—",  "—"),
    ("04-17", 5.06, "—",  "—"),
    ("04-25", 7.33, "142","10:25/km ⚠️ HR>135"),
]

def yn(val):
    if val is True:  return "✅"
    if val is False: return "❌"
    return "?"

def color_deficit(d):
    if d >= 1000: return "#4CAF50"
    if d >= 500:  return "#FFC107"
    return "#F44336"

# ── GUI ───────────────────────────────────────────────────────────────────────

def build_gui():
    with tg.Connection() as c:
        a = tg.Activity(c, dialog=False)
        a.settheme(dark=True)

        root = tg.NestedScrollView(a)
        layout = tg.LinearLayout(a, root, vertical=True)

        def header(text, color="#00BCD4"):
            tv = tg.TextView(a, text, layout)
            tv.settextsize(18)
            tv.setpadding(12, 16, 12, 4)
            tv.settextcolor(color)
            return tv

        def row_text(text, parent, size=14, color="#FFFFFF", padding=(8,2,8,2)):
            tv = tg.TextView(a, text, parent)
            tv.settextsize(size)
            tv.setpadding(*padding)
            tv.settextcolor(color)
            return tv

        def divider():
            sp = tg.Space(a, layout)
            sp.setheight(1)
            sp.setbackgroundcolor("#333333")

        # ── Title ────────────────────────────────────────────────────────────
        title = tg.TextView(a, f"🏋️ PJ's Life Coach Dashboard\n{TODAY.strftime('%A, %d %B %Y')}", layout)
        title.settextsize(20)
        title.setpadding(12, 20, 12, 8)
        title.settextcolor("#00BCD4")

        # ── Scale reminder ───────────────────────────────────────────────────
        last_scale = date(2026, 4, 25)
        next_due   = last_scale + timedelta(days=7)
        days_left  = (next_due - TODAY).days
        if days_left <= 0:
            scale_tv = tg.TextView(a, f"⚠️ SCALE CHECK OVERDUE — send HealthU+ screenshot!", layout)
            scale_tv.settextcolor("#F44336")
        else:
            scale_tv = tg.TextView(a, f"📊 Next scale check: {next_due} ({days_left} days)", layout)
            scale_tv.settextcolor("#9E9E9E")
        scale_tv.settextsize(14)
        scale_tv.setpadding(12, 4, 12, 12)

        divider()

        # ── Goals ────────────────────────────────────────────────────────────
        header("🎯 Goals")
        goals = [
            ("Weight",       f"{BODY_COMP['weight']:.2f} kg", f"{WEIGHT_GOAL} kg",  f"-{BODY_COMP['weight']-WEIGHT_GOAL:.2f} kg"),
            ("Visceral Fat", str(BODY_COMP['vf']),             f"< {VF_GOAL}",        f"-{BODY_COMP['vf']-VF_GOAL} pts"),
            ("Body Fat",     f"{BODY_COMP['bf']}%",            "< 18%",              f"-{BODY_COMP['bf']-18:.1f}%"),
            ("HbA1c",        "6.8%",                           "< 6.5%",             "next test"),
        ]
        for name, now, target, gap in goals:
            gl = tg.LinearLayout(a, layout, vertical=False)
            row_text(f"  {name}", gl, size=14, color="#BBBBBB")
            row_text(now, gl, size=14, color="#FFFFFF")
            row_text(f"  →  {target}", gl, size=13, color="#9E9E9E")
            row_text(f"  [{gap}]", gl, size=13, color="#F44336")

        divider()

        # ── Body comp ────────────────────────────────────────────────────────
        header("⚖️ Body Composition  (Apr 25)")
        metrics = [
            ("Weight",      f"{BODY_COMP['weight']} kg"),
            ("BMR",         f"{BODY_COMP['bmr']} kcal"),
            ("Body Fat",    f"{BODY_COMP['bf']}%"),
            ("Muscle Mass", f"{BODY_COMP['muscle']} kg"),
            ("Visceral Fat",f"{BODY_COMP['vf']}  (target <10)"),
        ]
        for label, val in metrics:
            ml = tg.LinearLayout(a, layout, vertical=False)
            row_text(f"  {label}:", ml, size=14, color="#9E9E9E")
            row_text(f"  {val}", ml, size=14, color="#FFFFFF")

        divider()

        # ── Weekly deficit ───────────────────────────────────────────────────
        header("🔥 Weekly Deficit  (Apr 21–27)")
        total_deficit = sum(d["tdee"] - d["eaten"] for d in DAILY_DATA.values())
        pct = min(100, int(total_deficit / WEEKLY_TARGET * 100))

        for day, d in DAILY_DATA.items():
            deficit = d["tdee"] - d["eaten"]
            dl = tg.LinearLayout(a, layout, vertical=False)
            row_text(f"  {day}", dl, size=13, color="#BBBBBB")
            row_text(f"  ate {d['eaten']:,}", dl, size=13, color="#FFFFFF")
            row_text(f"  TDEE {d['tdee']:,}", dl, size=13, color="#9E9E9E")
            dc = tg.TextView(a, f"  +{deficit:,}", dl)
            dc.settextsize(13)
            dc.settextcolor(color_deficit(deficit))

        total_tv = tg.TextView(a, f"\n  TOTAL DEFICIT:  {total_deficit:,} / {WEEKLY_TARGET:,} kcal  ({pct}%)", layout)
        total_tv.settextsize(15)
        total_tv.settextcolor("#4CAF50" if pct >= 100 else "#FFC107")
        total_tv.setpadding(12, 4, 12, 4)

        pb = tg.ProgressBar(a, layout)
        pb.setprogress(pct)
        pb.setpadding(12, 4, 12, 12)

        remaining = max(0, WEEKLY_TARGET - total_deficit)
        if remaining > 0:
            rem_tv = tg.TextView(a, f"  Still needed: {remaining:,} kcal (rest of Sat + Sun)", layout)
            rem_tv.settextsize(13)
            rem_tv.settextcolor("#FFC107")
            rem_tv.setpadding(12, 0, 12, 8)

        divider()

        # ── Habit scorecard ──────────────────────────────────────────────────
        header("📋 Habit Scorecard")
        hdr = tg.LinearLayout(a, layout, vertical=False)
        for h in ["  Date ", "Gym", "Run", "Kriy", "Weed✗", "Step"]:
            ht = tg.TextView(a, h, hdr)
            ht.settextsize(12)
            ht.settextcolor("#9E9E9E")
            ht.setpadding(4, 2, 4, 2)

        for day, d in DAILY_DATA.items():
            hl = tg.LinearLayout(a, layout, vertical=False)
            steps_ok = d["steps"] >= 15
            for val in [
                f"  {day} ",
                yn(d["gym"]),
                yn(d["run"]),
                yn(d["kriya"]),
                yn(d["weed_clean"]),
                yn(steps_ok),
            ]:
                ht = tg.TextView(a, val, hl)
                ht.settextsize(13)
                ht.setpadding(6, 3, 6, 3)

        divider()

        # ── Running history ──────────────────────────────────────────────────
        header("🏃 Running Progress")
        for dt, dist, hr, notes in RUNS:
            rl = tg.LinearLayout(a, layout, vertical=False)
            row_text(f"  {dt}", rl, size=13, color="#BBBBBB")
            row_text(f"  {dist}km", rl, size=13, color="#FFFFFF")
            row_text(f"  HR:{hr}", rl, size=13, color="#F44336" if hr != "—" and int(hr) > 135 else "#4CAF50")
            row_text(f"  {notes}", rl, size=12, color="#9E9E9E")

        header("📅 MAF Plan (next: Apr 28)", color="#9E9E9E")
        plan = [
            ("Wk1 Apr28", "2.5km", "3km", "5km"),
            ("Wk2 May5",  "2.5km", "3km", "5.5km"),
            ("Wk3 May12", "3km",   "3.5km","6km"),
            ("Wk8 Jun16", "4km",   "4.5km","8km"),
        ]
        for wk, tue, thu, sat in plan:
            pl = tg.LinearLayout(a, layout, vertical=False)
            color = "#00BCD4" if "Wk1" in wk else "#9E9E9E"
            row_text(f"  {wk}", pl, size=13, color=color)
            row_text(f"  Tue:{tue}", pl, size=12, color="#BBBBBB")
            row_text(f"  Thu:{thu}", pl, size=12, color="#BBBBBB")
            row_text(f"  Sat:{sat}", pl, size=12, color="#BBBBBB")

        divider()

        # ── Footer ───────────────────────────────────────────────────────────
        footer = tg.TextView(a, "\n  Non-negotiables: Gym/Run · 15k steps · <1200 cal · 80-90g protein · Veg first · Post-meal move · Kriya · No weed · Parents\n", layout)
        footer.settextsize(11)
        footer.settextcolor("#616161")
        footer.setpadding(12, 4, 12, 20)

        # Keep alive until dismissed
        for ev in a.events():
            if ev.type == tg.Event.destroy:
                break

if __name__ == "__main__":
    build_gui()
