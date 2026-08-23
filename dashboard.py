#!/usr/bin/env python3
"""
PJ's Life Coach Dashboard — dynamic from index.json
Run: python3 dashboard.py
"""

import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
except ImportError:
    print("Run: pip install rich")
    sys.exit(1)

try:
    import plotext as plt
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False

console = Console()
BASE = Path("/storage/emulated/0/Documents/claude/life-coach")
INDEX_FILE = BASE / "logs/index.json"
TODAY = date.today()

BMR = 1635
WEIGHT_GOAL = 76.0
VF_GOAL = 10
BF_GOAL = 18.0
WEEKLY_DEFICIT_TARGET = 7000

BODY_COMP_HISTORY = [
    ("2026-04-25", 80.25, 23.7, 55.1, 13, 1631),
    ("2026-05-02", 79.90, 23.5, 55.0, 13, 1635),
    ("2026-05-05", 79.55, None, None, None, None),
]


def load_index():
    data = json.loads(INDEX_FILE.read_text())
    return {e["date"]: e for e in data.get("entries", [])}


def yn(val):
    if val is True:  return "[green]✅[/green]"
    if val is False: return "[red]❌[/red]"
    return "[dim]?[/dim]"


def get_week_dates(ref_date=None):
    d = ref_date or TODAY
    monday = d - timedelta(days=d.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def render_header():
    now = datetime.now().strftime("%A, %d %B %Y  %H:%M IST")
    console.print(Rule(f"[bold cyan]PJ's Life Coach Dashboard[/bold cyan]  [dim]{now}[/dim]"))
    console.print()


def render_body_comp():
    console.print(Panel("[bold]Body Composition[/bold]", style="cyan", box=box.SIMPLE))

    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    t.add_column("Date", style="bold")
    t.add_column("Weight", justify="right")
    t.add_column("Body Fat", justify="right")
    t.add_column("Muscle", justify="right")
    t.add_column("Visc Fat", justify="right")
    t.add_column("BMR", justify="right")

    for d, wt, bf, mu, vf, bmr in BODY_COMP_HISTORY:
        t.add_row(
            d[5:],
            f"{wt:.2f} kg",
            f"{bf}%" if bf else "—",
            f"{mu} kg" if mu else "—",
            str(vf) if vf else "—",
            str(bmr) if bmr else "—",
        )

    latest_wt = BODY_COMP_HISTORY[-1][1]
    gap = latest_wt - WEIGHT_GOAL
    bar_len = 40
    start_wt = BODY_COMP_HISTORY[0][1]
    lost = start_wt - latest_wt
    total_to_lose = start_wt - WEIGHT_GOAL
    pct = min(100, max(0, int(lost / total_to_lose * 100))) if total_to_lose > 0 else 0
    filled = int(bar_len * pct / 100)
    bar = "[green]" + "█" * filled + "[/green][dim]" + "░" * (bar_len - filled) + "[/dim]"

    console.print(t)
    console.print(f"  Weight progress: {bar} [bold]{pct}%[/bold]  ({latest_wt:.2f}kg → {WEIGHT_GOAL}kg, {gap:.2f}kg left)")
    console.print()


def render_habit_scorecard(entries):
    console.print(Panel("[bold]Habit Scorecard — This Week[/bold]", style="cyan", box=box.SIMPLE))

    week = get_week_dates()

    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    t.add_column("Day", style="bold")
    t.add_column("Gym", justify="center")
    t.add_column("Run", justify="center")
    t.add_column("Steps", justify="center")
    t.add_column("Cal", justify="center")
    t.add_column("Kriya", justify="center")
    t.add_column("Weed✗", justify="center")
    t.add_column("Parents", justify="center")
    t.add_column("Veg1st", justify="center")
    t.add_column("Move", justify="center")

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    greens = 0
    total_cells = 0

    for i, d in enumerate(week):
        ds = d.isoformat()
        e = entries.get(ds, {})
        h = e.get("habits", {})

        is_today = d == TODAY
        is_future = d > TODAY
        label = f"{'→ ' if is_today else ''}{day_names[i]} {d.strftime('%d')}"

        if is_future:
            t.add_row(label, *["[dim]—[/dim]"] * 9, style="dim")
            continue

        gym_v = h.get("gym")
        run_v = h.get("run")
        steps_v = h.get("steps_15k")
        cal_v = h.get("calories_under_1200")
        kriya_v = h.get("kriya")
        weed_v = h.get("weed")
        weed_display = yn(True) if weed_v is False else (yn(False) if weed_v is True else yn(None))
        parents_v = h.get("parents_called")
        veg_v = h.get("veg_first")
        move_v = h.get("post_meal_move")

        vals = [gym_v, steps_v, cal_v, kriya_v, parents_v, veg_v, move_v]
        if weed_v is not None:
            vals.append(not weed_v)
        for v in vals:
            if v is not None:
                total_cells += 1
                if v:
                    greens += 1

        style = "bold" if is_today else ""
        t.add_row(
            label,
            yn(gym_v), yn(run_v), yn(steps_v), yn(cal_v),
            yn(kriya_v), weed_display, yn(parents_v), yn(veg_v), yn(move_v),
            style=style,
        )

    console.print(t)
    if total_cells > 0:
        hit_rate = int(greens / total_cells * 100)
        console.print(f"  Habit hit rate this week: [bold cyan]{hit_rate}%[/bold cyan] ({greens}/{total_cells})")
    console.print()


def render_recent_days(entries):
    console.print(Panel("[bold]Last 7 Days — Summary[/bold]", style="cyan", box=box.SIMPLE))

    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    t.add_column("Date", style="bold")
    t.add_column("Summary")
    t.add_column("Mood")

    dates = sorted(entries.keys(), reverse=True)[:7]
    for ds in dates:
        e = entries[ds]
        summary = e.get("summary", "—")
        if len(summary) > 80:
            summary = summary[:77] + "..."
        mood = e.get("mood_arc", "—")
        if len(mood) > 30:
            mood = mood[:27] + "..."
        t.add_row(ds[5:], summary, mood)

    console.print(t)
    console.print()


def render_goals():
    console.print(Panel("[bold]Goals at a Glance[/bold]", style="cyan", box=box.SIMPLE))

    latest_wt = BODY_COMP_HISTORY[-1][1]
    latest_vf = None
    latest_bf = None
    for entry in reversed(BODY_COMP_HISTORY):
        if entry[4] is not None and latest_vf is None:
            latest_vf = entry[4]
        if entry[2] is not None and latest_bf is None:
            latest_bf = entry[2]

    t = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold magenta")
    t.add_column("Goal", style="bold")
    t.add_column("Current", justify="right")
    t.add_column("Target", justify="right")
    t.add_column("Gap", justify="right")

    wt_gap = latest_wt - WEIGHT_GOAL
    t.add_row("Weight", f"{latest_wt:.2f}kg", f"{WEIGHT_GOAL}kg", f"[red]{wt_gap:.2f}kg[/red]")
    if latest_vf is not None:
        vf_gap = latest_vf - VF_GOAL
        t.add_row("Visceral Fat", str(latest_vf), f"<{VF_GOAL}", f"[red]{vf_gap}[/red]")
    if latest_bf is not None:
        bf_gap = latest_bf - BF_GOAL
        t.add_row("Body Fat", f"{latest_bf}%", f"<{BF_GOAL}%", f"[red]{bf_gap:.1f}%[/red]")
    t.add_row("HbA1c", "6.8%", "<6.5%", "[dim]next test[/dim]")
    t.add_row("Protein ceiling", "80-90g/day", "≤90g", "[dim]kidney[/dim]")

    console.print(t)
    console.print()


def render_scale_reminder():
    last_scale = None
    for entry in reversed(BODY_COMP_HISTORY):
        if entry[2] is not None:
            last_scale = date.fromisoformat(entry[0])
            break

    if last_scale is None:
        last_scale = date(2026, 4, 25)

    days_since = (TODAY - last_scale).days

    if days_since >= 7:
        console.print(Panel(
            f"[bold red]SCALE CHECK OVERDUE[/bold red]\n"
            f"Last full reading: {last_scale}  ({days_since} days ago)\n"
            f"[bold]Send HealthU+ screenshot — weight, BMR, visceral fat, body fat, muscle mass[/bold]",
            style="red", box=box.HEAVY
        ))
    else:
        next_due = last_scale + timedelta(days=7)
        days_to = (next_due - TODAY).days
        console.print(Panel(
            f"[dim]Next scale check in [bold]{days_to} days[/bold]  (due {next_due})[/dim]",
            style="dim", box=box.SIMPLE
        ))
    console.print()


def render_streak(entries):
    console.print(Panel("[bold]Streaks[/bold]", style="cyan", box=box.SIMPLE))

    streaks = {"gym": 0, "kriya": 0, "weed_clean": 0, "parents": 0, "steps_15k": 0}

    d = TODAY
    for _ in range(30):
        ds = d.isoformat()
        e = entries.get(ds, {})
        h = e.get("habits", {})
        if not h:
            break

        gym_today = h.get("gym") is True or h.get("run") is True
        kriya_today = h.get("kriya") is True
        weed_clean_today = h.get("weed") is False
        parents_today = h.get("parents_called") is True
        steps_today = h.get("steps_15k") is True

        checks = [
            ("gym", gym_today),
            ("kriya", kriya_today),
            ("weed_clean", weed_clean_today),
            ("parents", parents_today),
            ("steps_15k", steps_today),
        ]

        for key, val in checks:
            if val and streaks[key] == (TODAY - d).days:
                streaks[key] += 1

        d -= timedelta(days=1)

    labels = {"gym": "Gym/Run", "kriya": "Kriya", "weed_clean": "Weed-free", "parents": "Parents", "steps_15k": "Steps 15k"}
    parts = []
    for key, label in labels.items():
        n = streaks[key]
        color = "green" if n >= 3 else ("yellow" if n >= 1 else "red")
        parts.append(f"[{color}]{label}: {n}d[/{color}]")

    console.print("  " + "   ".join(parts))
    console.print()


def render_weight_chart():
    if not HAS_PLOTEXT or len(BODY_COMP_HISTORY) < 2:
        return

    console.print(Panel("[bold]Weight Trend[/bold]", style="cyan", box=box.SIMPLE))

    weights = [x[1] for x in BODY_COMP_HISTORY]
    labels = [x[0][5:] for x in BODY_COMP_HISTORY]
    xs = list(range(len(weights)))

    plt.clf()
    plt.plot_size(60, 12)
    plt.theme("dark")
    plt.plot(xs, weights, marker="braille", label="Weight kg")
    plt.xticks(xs, labels)
    plt.hline(WEIGHT_GOAL, color="red")
    plt.title(f"Weight → {WEIGHT_GOAL}kg goal")
    plt.ylim(WEIGHT_GOAL - 1, max(weights) + 0.5)
    plt.show()
    console.print()


def main():
    entries = load_index()
    render_header()
    render_scale_reminder()
    render_goals()
    render_body_comp()
    render_streak(entries)
    render_habit_scorecard(entries)
    render_recent_days(entries)
    render_weight_chart()
    console.print(Rule("[dim]End of Dashboard[/dim]"))


if __name__ == "__main__":
    main()
