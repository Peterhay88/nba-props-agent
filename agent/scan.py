"""Main scan. python -m agent.scan --run main|update"""
import argparse
from datetime import timedelta
from . import odds, store, tg, rules, sync
from .config import (BOOKS, ODDS_MIN, ODDS_MAX, MIN_EDGE, SEASON_END_SKIP, BLOWOUT_SPREAD, MIN_GAMES,
                     SLATE_HOURS, DRY_RUN, STAT_NAME)
from .espn import Espn, tkey
from .model import project, prob_over
from .util import now_utc, parse_ts, syd_date, et_date, norm, SYD


def match_espn(espn, ev):
    tip = parse_ts(ev["commence_time"])
    h, a = tkey(ev["home_team"]), tkey(ev["away_team"])
    for d in (et_date(tip), et_date(tip) - timedelta(days=1)):
        for g in espn.scoreboard(d):
            if g["home"] == h and g["away"] == a:
                return g
    return None


def find_athlete(roster, name):
    n = norm(name)
    if n in roster:
        return roster[n]
    parts = n.split()
    for k, v in roster.items():
        kp = k.split()
        if kp and parts and kp[-1] == parts[-1] and kp[0][:1] == parts[0][:1]:
            return v
    return None


def team_context(espn, team_id, team_key, tip, injuries, rosters):
    """Back-to-back flag, recent team game ids, and the most prominent teammate who is out."""
    games = [g for g in espn.team_games(team_id) if g[1] < tip - timedelta(hours=3)]
    b2b = any(et_date(d) == et_date(tip) - timedelta(days=1) for _, d in games)
    recent5 = [eid for eid, _ in games[-5:]]
    out_star = None
    best = 0
    for nm, inj in injuries.items():
        if inj["team"] != team_key or inj["status"].lower() != "out":
            continue
        aid = rosters[team_id].get(nm)
        if not aid:
            continue
        gl = espn.gamelog(aid)
        if not gl or (tip - gl[0]["date"]).days > 14:
            continue
        avg = {k: sum(g[k] for g in gl) / len(gl) for k in ("pts", "reb", "ast", "min")}
        score = avg["pts"] + avg["ast"] * 1.5
        if (avg["pts"] >= 15 or avg["ast"] >= 5 or avg["reb"] >= 8) and avg["min"] >= 24 and score > best:
            best, out_star = score, inj["name"]
    return {"b2b": b2b, "recent5": recent5, "out_star": out_star}


def evaluate_event(ev, espn, injuries, standings, spread):
    """Returns (candidates, skip_reasons)."""
    tip = parse_ts(ev["commence_time"])
    skips = []
    g = match_espn(espn, ev)
    if not g:
        return [], [f"{ev['away_team']} @ {ev['home_team']}: no ESPN match"]
    if spread is not None and spread >= BLOWOUT_SPREAD:
        return [], [f"{ev['away_team']} @ {ev['home_team']}: blowout risk (spread {spread})"]
    props = odds.props(ev["id"])
    if not props:
        return [], [f"{ev['away_team']} @ {ev['home_team']}: no props posted"]
    rosters = {g["home_id"]: espn.roster(g["home_id"]), g["away_id"]: espn.roster(g["away_id"])}
    side = {g["home_id"]: (True, g["home"], g["away"]), g["away_id"]: (False, g["away"], g["home"])}
    tctx = {tid: team_context(espn, tid, side[tid][1], tip, injuries, rosters) for tid in rosters}
    lg = list(standings.values())
    lg_pa = sum(x[1] for x in lg) / len(lg) if lg else 0
    lg_tot = sum(x[0] + x[1] for x in lg) / len(lg) if lg else 0
    game_label = f"{ev['away_team'].split()[-1]} @ {ev['home_team'].split()[-1]}"
    cands = []
    seen_players = {}
    for (pn, stat), rec in props.items():
        if pn in seen_players and seen_players[pn] is None:
            continue
        tid = next((t for t in rosters if find_athlete(rosters[t], rec["player"])), None)
        if not tid:
            continue
        is_home, team_key, opp_key = side[tid]
        tc = tctx[tid]
        name = rec["player"]
        if pn not in seen_players:
            reason = None
            inj = injuries.get(pn)
            if inj:
                reason = "minutes restriction" if "minute" in inj["comment"] else f"injury list ({inj['status']})"
            elif tc["b2b"]:
                reason = "back-to-back"
            seen_players[pn] = None if reason else espn.gamelog(find_athlete(rosters[tid], name))
            gl = seen_players[pn]
            if not reason and (not gl or len(gl) < MIN_GAMES):
                reason = "small sample"
            if not reason:
                played = {x["event_id"] for x in gl}
                missed = sum(1 for e in tc["recent5"] if e not in played)
                mins = [x["min"] for x in gl[:10]]
                if missed >= 2:
                    reason = "returning from absence"
                elif len(mins) >= 5 and mins[0] < 0.65 * (sum(mins[1:]) / len(mins[1:])):
                    reason = "minutes drop (possible restriction)"
            if reason:
                seen_players[pn] = None
                skips.append(f"{name}: {reason}")
                continue
        gl = seen_players[pn]
        if not gl:
            continue
        sd = standings.get(opp_key)
        opp_def = sd[1] / lg_pa if sd and lg_pa else None
        pace = (sd[0] + sd[1]) / lg_tot if sd and lg_tot else None
        mu, sigma, last, flags = project(gl, stat, is_home, opp_def, pace, tc["out_star"])
        # reference (main) line: the Over price closest to $1.90
        pool = rec["main"] or rec["alts"]
        ref = min(pool, key=lambda x: abs(x[2] - 1.90)) if pool else None
        if not ref:
            continue
        best_by_line = {}
        for book, point, px in rec["alts"] + rec["main"]:
            if ODDS_MIN <= px <= ODDS_MAX and point <= ref[1]:
                if point not in best_by_line or px > best_by_line[point][1]:
                    best_by_line[point] = (book, px)
        best = None
        for point, (book, px) in best_by_line.items():
            p, hits = prob_over(point, mu, sigma, last)
            edge = p * px - 1
            if best is None or edge > best["edge"]:
                best = {"line": point, "book": book, "odds": px, "edge": edge, "p": p, "hits": hits}
        if not best or best["edge"] < MIN_EDGE:
            continue
        form = f"Last 10: {best['hits']}/{len(last)} over"
        cands.append({"player": name, "pn": pn, "stat": stat, "line": best["line"], "book": best["book"],
                      "odds": best["odds"], "edge": best["edge"], "p": best["p"], "mu": mu,
                      "ref_line": ref[1], "ref_odds": ref[2], "hits": best["hits"],
                      "flags": "; ".join([form] + flags), "odds_event_id": ev["id"], "espn_event_id": g["id"],
                      "game": game_label, "tip": tip})
    return cands, skips


def fmt_pick(n, c, stake_amt, pct):
    tier = ", top tier" if pct >= 0.10 else ""
    return (f"{n}. {c['player']} o{c['line']:g} {STAT_NAME[c['stat']]} @ ${c['odds']:.2f} {BOOKS[c['book']]}\n"
            f"   {c['game']} · main line o{c['ref_line']:g} @ ${c['ref_odds']:.2f} · edge {100 * c['edge']:.1f}%\n"
            f"   {c['flags']}\n"
            f"   Stake ${stake_amt} ({pct * 100:.0f}%{tier})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    run = ap.parse_args().run
    sync.process_updates()
    sync.settle()
    today = syd_date()
    if today.isoformat() >= SEASON_END_SKIP:
        print("Season-end skip window")
        return
    bets = store.bets()
    ctx = rules.context(bets)
    head = "TEST RUN - don't bet\n" if DRY_RUN else ""
    if ctx["stop"]:
        if run == "main":
            tg.send(f"{head}Props agent {run} run\n{ctx['stop']}\n\n{sync.status_text(bets)}")
        print("STOP:", ctx["stop"])
        return
    now = now_utc()
    evs = [e for e in odds.events()
           if now + timedelta(minutes=10) < parse_ts(e["commence_time"]) < now + timedelta(hours=SLATE_HOURS)]
    if not evs:
        if run == "main":
            tg.send(f"{head}Props agent: no NBA games on today's slate.")
        return
    espn = Espn()
    injuries, standings = espn.injuries(), espn.standings()
    spreads = odds.spreads()
    cands, skips = [], []
    for ev in evs:
        c, s = evaluate_event(ev, espn, injuries, standings, spreads.get(ev["id"]))
        cands += c
        skips += s
        print(f"{ev['away_team']} @ {ev['home_team']}: {len(c)} qualified, {len(s)} skipped")
    # one pick per player (best edge), ranked
    best = {}
    for c in cands:
        if c["pn"] not in best or c["edge"] > best[c["pn"]]["edge"]:
            best[c["pn"]] = c
    ranked = sorted(best.values(), key=lambda c: c["edge"], reverse=True)
    picks = store.picks()
    todays = [p for p in picks if p["date"] == today.isoformat()]
    sent_keys = {(norm(p["player"]), p["stat"]) for p in todays if p["type"] == "single" and p["status"] == "suggested"}
    next_n = max([int(p["n"]) for p in todays] + [0]) + 1
    new_rows, lines, buttons = [], [], []

    # update runs: withdraw earlier picks for games not started that no longer qualify
    withdrawn = []
    if run != "main":
        live_keys = {(c["pn"], c["stat"]) for c in ranked}
        placed = {b["pick_id"] for b in bets}
        for p in todays:
            if (p["type"] == "single" and p["status"] == "suggested" and parse_ts(p["tip_utc"]) > now
                    and (norm(p["player"]), p["stat"]) not in live_keys and p["pick_id"] not in placed):
                p["status"] = "withdrawn"
                withdrawn.append(p)
        ranked = [c for c in ranked if (c["pn"], c["stat"]) not in sent_keys]

    slots = ctx["slots"]
    chosen = ranked[:slots]
    for c in chosen:
        amt, pct = rules.stake(c["edge"], ctx)
        if not amt:
            continue
        pid = f"{today:%Y%m%d}-{next_n}"
        new_rows.append({"pick_id": pid, "date": today.isoformat(), "run": run, "n": next_n, "type": "single",
                         "odds_event_id": c["odds_event_id"], "espn_event_id": c["espn_event_id"], "game": c["game"],
                         "tip_utc": c["tip"].isoformat(), "player": c["player"], "stat": c["stat"],
                         "line": f"{c['line']:g}", "book": BOOKS[c["book"]], "odds": f"{c['odds']:.2f}",
                         "edge": f"{c['edge']:.4f}", "model_p": f"{c['p']:.3f}", "mu": f"{c['mu']:.1f}",
                         "ref_line": f"{c['ref_line']:g}", "ref_odds": f"{c['ref_odds']:.2f}", "hits10": c["hits"],
                         "stake": amt, "flags": c["flags"], "status": "suggested", "dry_run": "1" if DRY_RUN else "0"})
        lines.append(fmt_pick(next_n, c, amt, pct))
        buttons.append([{"text": f"#{next_n} Placed", "callback_data": f"P|{pid}"},
                        {"text": f"#{next_n} Skip", "callback_data": f"S|{pid}"}])
        next_n += 1
    # multi option: top two singles from different games
    singles = [r for r in new_rows if r["type"] == "single"]
    if run == "main" and len(singles) >= 2:
        a = singles[0]
        b = next((r for r in singles[1:] if r["odds_event_id"] != a["odds_event_id"]), None)
        amt, _ = rules.stake(0, ctx, multi=True)
        if b and amt:
            pid = f"{today:%Y%m%d}-{next_n}"
            o = float(a["odds"]) * float(b["odds"])
            new_rows.append({"pick_id": pid, "date": today.isoformat(), "run": run, "n": next_n, "type": "multi",
                             "legs": f"{a['pick_id']}+{b['pick_id']}", "player": f"#{a['n']} + #{b['n']}",
                             "tip_utc": max(a["tip_utc"], b["tip_utc"]), "book": a["book"] if a["book"] == b["book"] else "Mixed",
                             "odds": f"{o:.2f}", "stake": amt, "status": "suggested",
                             "dry_run": "1" if DRY_RUN else "0"})
            lines.append(f"{next_n}. Multi option: #{a['n']} + #{b['n']} @ ${o:.2f} · different games\n"
                         f"   Stake ${amt} (5%) · uses 1 of your 4 daily bets")
            buttons.append([{"text": f"#{next_n} Placed", "callback_data": f"P|{pid}"},
                            {"text": f"#{next_n} Skip", "callback_data": f"S|{pid}"}])
    store.save_picks(picks + new_rows)

    skip_kinds = {}
    for s in skips:
        k = s.split(": ", 1)[-1].split(" (")[0]
        skip_kinds[k] = skip_kinds.get(k, 0) + 1
    skip_txt = ", ".join(f"{v}x {k}" for k, v in sorted(skip_kinds.items(), key=lambda x: -x[1]))
    when = now.astimezone(SYD).strftime("%a %d %b %H:%M")
    foot = (f"Day room ${max(ctx['day_room'], 0):,.0f} · week room ${max(ctx['week_room'], 0):,.0f} · "
            f"bets {ctx['bets_today']} of 4 · odds credits left {odds.credits_left}")
    if run == "main":
        msg = [f"{head}Props agent · 10:00 run · {when}",
               f"{len(singles)} qualified · {len(evs)} games scanned", ""]
        msg += lines if lines else ["No bets qualified today. No bet is a fine result."]
        if skip_txt:
            msg += ["", f"Skipped: {skip_txt}"]
        msg += ["", foot]
        tg.send("\n".join(msg), None if DRY_RUN else buttons)
    elif lines or withdrawn:
        msg = [f"{head}Props agent · update · {when}"]
        for p in withdrawn:
            msg.append(f"WITHDRAWN #{p['n']} {p['player']} o{p['line']} {p['stat']}: no longer qualifies (injury news or price moved)")
        if lines:
            msg += ["New qualifiers:"] + lines
        msg += ["", foot]
        tg.send("\n".join(msg), None if DRY_RUN else buttons)
    print("\n".join(lines) or "no picks")
    print("Skipped:", skip_txt)
    print("Credits left:", odds.credits_left)


if __name__ == "__main__":
    main()
