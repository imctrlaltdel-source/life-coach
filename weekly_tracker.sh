#!/bin/bash
# PJ Weekly Tracker — Steps + Deficit
# Usage: bash weekly_tracker.sh

# ===== DATA — EDIT THESE =====
#         Steps   CalIn  CalOut
SUN_S=23000; SUN_I=1399; SUN_O=2380
MON_S=12000; MON_I=937;  MON_O=2035
TUE_S=0;     TUE_I=0;    TUE_O=0
WED_S=0;     WED_I=0;    WED_O=0
THU_S=0;     THU_I=0;    THU_O=0
FRI_S=0;     FRI_I=0;    FRI_O=0
SAT_S=0;     SAT_I=0;    SAT_O=0

STEP_GOAL=105000
DEF_GOAL=4900

DAYS=(Sun Mon Tue Wed Thu Fri Sat)
MARKS=(S M T W T F A)
STEPS=($SUN_S $MON_S $TUE_S $WED_S $THU_S $FRI_S $SAT_S)
CAL_I=($SUN_I $MON_I $TUE_I $WED_I $THU_I $FRI_I $SAT_I)
CAL_O=($SUN_O $MON_O $TUE_O $WED_O $THU_O $FRI_O $SAT_O)

# ===== CALC =====
tot_s=0; tot_d=0; days_done=0
DEFS=()
for i in 0 1 2 3 4 5 6; do
    tot_s=$((tot_s + ${STEPS[$i]}))
    if [ "${CAL_O[$i]}" -gt 0 ] && [ "${CAL_I[$i]}" -gt 0 ]; then
        d=$((${CAL_O[$i]} - ${CAL_I[$i]}))
        DEFS+=($d)
        tot_d=$((tot_d + d))
        days_done=$((days_done + 1))
    else
        DEFS+=(0)
    fi
done

left=$((7 - days_done))
s_left=$((STEP_GOAL - tot_s)); [ $s_left -lt 0 ] && s_left=0
d_left=$((DEF_GOAL - tot_d)); [ $d_left -lt 0 ] && d_left=0
if [ $left -gt 0 ]; then
    s_need=$((s_left / left))
    d_need=$((d_left / left))
else
    s_need=0; d_need=0
fi

s_pct=$((tot_s * 100 / STEP_GOAL))
d_pct=$((tot_d * 100 / DEF_GOAL))

# ===== BAR FUNCTION (ASCII) =====
bar() {
    local val=$1 max=$2 w=${3:-30} char=${4:-#} filled
    filled=$((val * w / max))
    [ $filled -gt $w ] && filled=$w
    [ $filled -lt 0 ] && filled=0
    local b="" e=""
    for ((j=0; j<filled; j++)); do b+="$char"; done
    for ((j=filled; j<w; j++)); do e+="."; done
    echo "${b}${e}"
}

# ===== STACKED BAR (each day = its letter) =====
stacked() {
    local -n vals=$1
    local goal=$2 w=40
    local result=""
    for i in 0 1 2 3 4 5 6; do
        if [ "${vals[$i]}" -gt 0 ]; then
            local seg=$((${vals[$i]} * w / goal))
            [ $seg -lt 1 ] && seg=1
            for ((j=0; j<seg; j++)); do result+="${MARKS[$i]}"; done
        fi
    done
    local filled=${#result}
    [ $filled -gt $w ] && result="${result:0:$w}" && filled=$w
    for ((j=filled; j<w; j++)); do result+="."; done
    echo "$result"
}

echo ""
echo "========================================"
echo "  WEEKLY STEPS"
echo "  Goal: $STEP_GOAL (15k/day x 7)"
echo "  Done: $tot_s | Left: $s_left"
echo "  $left days remain -> $s_need/day needed"
echo "========================================"
echo ""

sb=$(stacked STEPS $STEP_GOAL)
echo "  [$sb] ${s_pct}%"
echo "  Legend: S=Sun M=Mon T=Tue W=Wed T=Thu F=Fri A=Sat"
echo ""

for i in 0 1 2 3 4 5 6; do
    s=${STEPS[$i]}
    if [ "$s" -eq 0 ]; then
        printf "  %s  ---\n" "${DAYS[$i]}"
    else
        b=$(bar $s 25000 25)
        printf "  %s  [%s] %s\n" "${DAYS[$i]}" "$b" "$s"
    fi
done

echo ""
echo "========================================"
echo "  WEEKLY DEFICIT"
echo "  Goal: $DEF_GOAL cal (700/day x 7)"
echo "  Done: $tot_d | Left: $d_left"
echo "  $left days remain -> $d_need/day needed"
echo "========================================"
echo ""

stacked_d() {
    local w=40 result=""
    for i in 0 1 2 3 4 5 6; do
        local d=${DEFS[$i]}
        if [ "$d" -gt 0 ]; then
            local seg=$((d * w / DEF_GOAL))
            [ $seg -lt 1 ] && seg=1
            for ((j=0; j<seg; j++)); do result+="${MARKS[$i]}"; done
        elif [ "$d" -lt 0 ]; then
            local seg=$(((-d) * w / DEF_GOAL))
            [ $seg -lt 1 ] && seg=1
            for ((j=0; j<seg; j++)); do result+="!"; done
        fi
    done
    local filled=${#result}
    [ $filled -gt $w ] && result="${result:0:$w}" && filled=$w
    for ((j=filled; j<w; j++)); do result+="."; done
    echo "$result"
}

sd=$(stacked_d)
echo "  [$sd] ${d_pct}%"
echo "  Legend: S=Sun M=Mon !=surplus .=remaining"
echo ""

for i in 0 1 2 3 4 5 6; do
    d=${DEFS[$i]}
    ci=${CAL_I[$i]}
    co=${CAL_O[$i]}
    if [ "$co" -eq 0 ]; then
        printf "  %s  ---\n" "${DAYS[$i]}"
    elif [ "$d" -lt 0 ]; then
        b=$(bar $((-d)) 1200 25)
        printf "  %s  [%s] -%d SURPLUS (ate:%d burn:%d)\n" "${DAYS[$i]}" "$b" "$((-d))" "$ci" "$co"
    else
        b=$(bar $d 1200 25)
        printf "  %s  [%s] %d  (ate:%d burn:%d)\n" "${DAYS[$i]}" "$b" "$d" "$ci" "$co"
    fi
done

echo ""
echo "  Updated: $(date '+%b %d %H:%M') | Edit DATA in weekly_tracker.sh"
echo ""
