"""Rulebook enforcement: bankroll, stakes, stops, breaches."""
from datetime import timedelta
from .config import (BANKROLL_START, STAKE_STD, STAKE_MAX, STAKE_MULTI, TOP_TIER_EDGE, DAY_STOP,
                     WEEK_STOP, MAX_BETS_DAY, DRAWDOWN_FLOOR, MIN_STAKE)
from .util import syd_date
from datetime import date as _date


def _d(s):
    return _date.fromisoformat(s)


def context(bets, today=None):
    today = today or syd_date()
    monday = today - timedelta(days=today.weekday())
    settled = [b for b in bets if b["status"] == "settled"]
    pl = lambda rows: sum(float(b["pl"] or 0) for b in rows)
    bankroll = BANKROLL_START + pl(settled)
    week_bankroll = BANKROLL_START + pl([b for b in settled if _d(b["date"]) < monday])
    today_rows = [b for b in bets if b["date"] == today.isoformat()]
    week_rows = [b for b in bets if monday <= _d(b["date"]) <= today]
    open_today = sum(float(b["stake"]) for b in today_rows if b["status"] == "open")
    open_week = sum(float(b["stake"]) for b in week_rows if b["status"] == "open")
    day_pl = pl([b for b in today_rows if b["status"] == "settled"])
    week_pl = pl([b for b in week_rows if b["status"] == "settled"])
    breaches_week = [b for b in week_rows if b["qualified"] == "N"]
    yday = (today - timedelta(days=1)).isoformat()
    ctx = {
        "today": today, "bankroll": bankroll, "week_bankroll": week_bankroll,
        "day_pl": day_pl, "week_pl": week_pl,
        "day_room": DAY_STOP + min(day_pl, 0) - open_today,
        "week_room": WEEK_STOP + min(week_pl, 0) - open_week,
        "bets_today": len(today_rows), "slots": MAX_BETS_DAY - len(today_rows),
        "breaches_week": len(breaches_week), "stop": None,
    }
    if bankroll <= DRAWDOWN_FLOOR:
        ctx["stop"] = f"Bankroll ${bankroll:,.0f} is at or below the ${DRAWDOWN_FLOOR:,.0f} floor. Betting stops until you've reviewed the ledger."
    elif len(breaches_week) >= 2:
        ctx["stop"] = "2 breaches this week. No betting until Monday."
    elif any(b["date"] == yday and b["qualified"] == "N" for b in bets):
        ctx["stop"] = "Breach yesterday, so today is a no-bet day."
    elif ctx["week_room"] < MIN_STAKE:
        ctx["stop"] = f"Weekly stop reached (week P/L ${week_pl:,.0f}). Done until Monday."
    elif ctx["day_room"] < MIN_STAKE:
        ctx["stop"] = f"Daily stop reached (day P/L ${day_pl:,.0f}). Done for today."
    elif ctx["slots"] <= 0:
        ctx["stop"] = f"{MAX_BETS_DAY} bets already placed today. Done for today."
    return ctx


def stake(edge, ctx, multi=False):
    pct = STAKE_MULTI if multi else (STAKE_MAX if edge >= TOP_TIER_EDGE else STAKE_STD)
    s = round(ctx["week_bankroll"] * pct / 10) * 10
    s = min(s, ctx["day_room"], ctx["week_room"])
    s = int(s // 10 * 10)
    return s if s >= MIN_STAKE else 0, pct
