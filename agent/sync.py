"""Processes Telegram taps/commands and settles finished games. Runs every 20 min on game days."""
from datetime import timedelta
from . import store, tg, rules
from .config import TG_CHAT, STATS
from .espn import Espn
from .util import now_utc, parse_ts, syd_date, norm

HELP = ("Commands:\n/b365 N ODDS  - placed pick N at Bet365\n/placed N [ODDS] [STAKE]  - placed pick N\n"
        "/bet STAKE ODDS description  - a bet the agent didn't pick (logged as a breach)\n"
        "/settle BETID win|loss|void  - settle a manual bet\n/status  - bankroll and limits")


def _desc(p):
    if p["type"] == "multi":
        return f"Multi {p['player']}"
    return f"{p['player']} o{p['line']} {p['stat']}"


def _place(pick, book, odds, stake, bets, note=""):
    if any(b["pick_id"] == pick["pick_id"] for b in bets):
        return f"#{pick['n']} is already logged."
    ctx = rules.context(bets)
    qualified = "Y" if ctx["slots"] > 0 else "N"
    bet_id = f"B{len(bets) + 1}"
    bets.append({"bet_id": bet_id, "date": syd_date().isoformat(), "pick_id": pick["pick_id"], "type": pick["type"],
                 "description": _desc(pick), "book": book, "odds": f"{odds:.2f}", "stake": f"{stake:.0f}",
                 "qualified": qualified, "status": "open", "result": "", "pl": "", "placed_utc": now_utc().isoformat()})
    msg = f"Logged {bet_id}: #{pick['n']} {_desc(pick)} @ ${odds:.2f} {book}, ${stake:.0f}{note}"
    if qualified == "N":
        msg += "\nBREACH: over the 4-bets-a-day limit. Tomorrow is a no-bet day."
    return msg


def _today_pick(picks, n):
    today = syd_date().isoformat()
    for p in picks:
        if p["date"] == today and p["n"] == str(n) and p["status"] == "suggested":
            return p
    return None


def status_text(bets):
    c = rules.context(bets)
    lines = [f"Bankroll ${c['bankroll']:,.0f} (Monday ${c['week_bankroll']:,.0f})",
             f"Today P/L ${c['day_pl']:+,.0f} · room ${max(c['day_room'], 0):,.0f}",
             f"Week P/L ${c['week_pl']:+,.0f} · room ${max(c['week_room'], 0):,.0f}",
             f"Bets today {c['bets_today']} of 4 · breaches this week {c['breaches_week']}"]
    if c["stop"]:
        lines.append("STOP: " + c["stop"])
    return "\n".join(lines)


def process_updates():
    st = store.state()
    ups = tg.updates(st.get("tg_offset", 0))
    if not ups:
        return
    picks, bets = store.picks(), store.bets()
    for u in ups:
        st["tg_offset"] = u["update_id"] + 1
        cb = u.get("callback_query")
        if cb:
            if str(cb["message"]["chat"]["id"]) != str(TG_CHAT):
                continue
            action, pid = (cb.get("data", "") + "|").split("|")[:2]
            pick = next((p for p in picks if p["pick_id"] == pid), None)
            if not pick:
                tg.answer(cb["id"], "Pick not found")
                continue
            if action == "P":
                msg = _place(pick, pick["book"], float(pick["odds"]), float(pick["stake"]), bets)
            else:
                msg = f"Skipped #{pick['n']} {_desc(pick)}"
            tg.answer(cb["id"], "Logged")
            tg.send(msg)
            continue
        m = u.get("message") or {}
        if str(m.get("chat", {}).get("id")) != str(TG_CHAT):
            continue
        parts = (m.get("text") or "").strip().split()
        if not parts:
            continue
        cmd = parts[0].lower().split("@")[0]
        try:
            if cmd == "/b365" and len(parts) >= 3:
                p = _today_pick(picks, parts[1])
                if not p:
                    tg.send(f"No pick #{parts[1]} today.")
                    continue
                odds = float(parts[2])
                note = "" if odds >= float(p["odds"]) else f" (lower than the {p['book']} ${p['odds']})"
                tg.send(_place(p, "Bet365", odds, float(p["stake"]), bets, note))
            elif cmd == "/placed" and len(parts) >= 2:
                p = _today_pick(picks, parts[1])
                if not p:
                    tg.send(f"No pick #{parts[1]} today.")
                    continue
                odds = float(parts[2]) if len(parts) > 2 else float(p["odds"])
                stake = float(parts[3]) if len(parts) > 3 else float(p["stake"])
                note = "" if stake <= float(p["stake"]) else " (above the rulebook stake)"
                tg.send(_place(p, p["book"], odds, stake, bets, note))
            elif cmd == "/bet" and len(parts) >= 4:
                stake, odds = float(parts[1]), float(parts[2])
                bet_id = f"B{len(bets) + 1}"
                bets.append({"bet_id": bet_id, "date": syd_date().isoformat(), "pick_id": "", "type": "manual",
                             "description": " ".join(parts[3:]), "book": "", "odds": f"{odds:.2f}",
                             "stake": f"{stake:.0f}", "qualified": "N", "status": "open", "result": "", "pl": "",
                             "placed_utc": now_utc().isoformat()})
                tg.send(f"Logged {bet_id} as a BREACH: not an agent-qualified bet.\n"
                        f"Settle it later with /settle {bet_id} win|loss.\nRule 7: tomorrow is a no-bet day.")
            elif cmd == "/settle" and len(parts) >= 3:
                b = next((x for x in bets if x["bet_id"].lower() == parts[1].lower()), None)
                res = parts[2].lower()
                if not b or res not in ("win", "loss", "void"):
                    tg.send("Usage: /settle BETID win|loss|void")
                    continue
                _settle_bet(b, res)
                tg.send(f"{b['bet_id']} settled: {res} {float(b['pl']):+,.0f}")
            elif cmd == "/status":
                tg.send(status_text(bets))
            else:
                tg.send(HELP)
        except ValueError:
            tg.send(HELP)
    store.save_picks(picks)
    store.save_bets(bets)
    store.save_state(st)


def _settle_bet(b, res):
    stake, odds = float(b["stake"]), float(b["odds"])
    b["result"] = res
    b["pl"] = f"{stake * (odds - 1):.2f}" if res == "win" else ("0" if res == "void" else f"{-stake:.2f}")
    b["status"] = "settled"


def settle():
    picks, bets = store.picks(), store.bets()
    espn = Espn()
    now = now_utc()
    boxes = {}
    changed = []
    for p in picks:
        if p["result"] or p["type"] != "single" or not p["espn_event_id"]:
            continue
        if parse_ts(p["tip_utc"]) > now - timedelta(hours=2, minutes=20):
            continue
        eid = p["espn_event_id"]
        if eid not in boxes:
            boxes[eid] = espn.box(eid)
        done, players = boxes[eid]
        if not done:
            continue
        row = players.get(norm(p["player"]))
        if not row or row.get("dnp"):
            p["result"], p["actual"] = "void", "DNP"
        else:
            actual = row[STATS[p["stat"]][3]]
            p["actual"] = f"{actual:.0f}"
            p["result"] = "win" if actual > float(p["line"]) else "loss"
        changed.append(p)
    by_id = {p["pick_id"]: p for p in picks}
    for p in picks:
        if p["type"] == "multi" and not p["result"]:
            legs = [by_id.get(x) for x in p["legs"].split("+")]
            if all(l and l["result"] for l in legs):
                res = [l["result"] for l in legs]
                p["result"] = "loss" if "loss" in res else ("void" if all(r == "void" for r in res) else "win")
                changed.append(p)
    settled_bets = []
    for b in bets:
        if b["status"] == "open" and b["pick_id"] in by_id and by_id[b["pick_id"]]["result"]:
            pk = by_id[b["pick_id"]]
            res = pk["result"]
            if pk["type"] == "multi" and res == "win":
                legs = [by_id[x] for x in pk["legs"].split("+")]
                live = [l for l in legs if l["result"] == "win"]
                b["odds"] = f"{float(b['odds']) if len(live) == len(legs) else float(live[0]['odds']):.2f}"
            _settle_bet(b, res)
            settled_bets.append(b)
    store.save_picks(picks)
    store.save_bets(bets)
    if settled_bets:
        lines = ["Results"]
        for b in settled_bets:
            pk = by_id[b["pick_id"]]
            act = f" ({pk['actual']})" if pk.get("actual") else ""
            lines.append(f"{'WIN' if b['result'] == 'win' else b['result'].upper()} {b['description']}{act} {float(b['pl']):+,.0f}")
        lines.append("")
        lines.append(status_text(bets))
        tg.send("\n".join(lines))
    elif changed and all(p["dry_run"] == "1" for p in changed):
        singles = [p for p in changed if p["type"] == "single"]
        if singles:
            w = sum(p["result"] == "win" for p in singles)
            l = sum(p["result"] == "loss" for p in singles)
            lines = [f"TEST picks graded: {w} won, {l} lost"]
            lines += [f"{p['result'].upper()} {p['player']} o{p['line']} {p['stat']} (actual {p['actual']})" for p in singles]
            tg.send("\n".join(lines))


def main():
    process_updates()
    settle()


if __name__ == "__main__":
    main()
