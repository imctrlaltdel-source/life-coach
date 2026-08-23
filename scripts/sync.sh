#!/usr/bin/env bash
# Cross-device sync: laptop <-> GitHub <-> Termux, via the same repo CLAUDE.md points at.
# Usage:
#   scripts/sync.sh pull   -> fetch + fast-forward-only merge (run at session start)
#   scripts/sync.sh push   -> commit + push db/logs/CLAUDE.md/cgm changes (run at session end and after logging real data)
#   scripts/sync.sh        -> pull then push (default, full round-trip)
#
# Never auto-resolves a real conflict (diverged history). If pull can't fast-forward,
# it stops and prints instructions instead of guessing — see the 2026-08-23 incident
# in CLAUDE.md's sync section for what manual resolution looks like.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

_pull() {
  git fetch origin
  if git merge origin/master --ff-only 2>/tmp/sync_pull_err.$$; then
    rm -f /tmp/sync_pull_err.$$
  else
    if grep -q "would be overwritten" /tmp/sync_pull_err.$$ 2>/dev/null; then
      echo "SYNC BLOCKED — local untracked files collide with incoming ones."
      echo "Do NOT delete anything. Run: git stash push -u -m 'pre-sync untracked'"
      echo "then retry, then verify with: git diff stash@{0}^3 HEAD -- <file> before dropping the stash."
    else
      echo "SYNC CONFLICT — history has diverged (both laptop and phone committed since last sync)."
      echo "Do not auto-resolve. Surface this to PJ and resolve by hand, the way the 2026-08-23 merge was done."
    fi
    cat /tmp/sync_pull_err.$$ 2>/dev/null
    rm -f /tmp/sync_pull_err.$$
    exit 1
  fi
}

_push() {
  git add db/coach.db logs/ CLAUDE.md cgm/ 2>/dev/null || true
  if ! git diff --cached --quiet; then
    git commit -m "sync: $(date '+%Y-%m-%d %H:%M IST')" -q
    git push origin master
  fi
}

case "${1:-both}" in
  pull) _pull ;;
  push) _push ;;
  both) _pull; _push ;;
  *) echo "usage: sync.sh [pull|push]"; exit 1 ;;
esac
