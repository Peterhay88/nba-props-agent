"""TheOddsAPI: NBA events, player props (main + alternate lines), spreads."""
from .config import BOOKS, STATS, ODDS_KEY
from .util import get_json, norm

BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"
BOOK_PARAM = ",".join(BOOKS)
credits_left = None


def _track(h):
    global credits_left
    if h and h.get("x-requests-remaining"):
        credits_left = h.get("x-requests-remaining")


def events():
    data, h = get_json(f"{BASE}/events", {"apiKey": ODDS_KEY})
    _track(h)
    return data or []


def spreads():
    """{event_id: absolute spread} (1 credit)."""
    data, h = get_json(f"{BASE}/odds", {"apiKey": ODDS_KEY, "bookmakers": BOOK_PARAM,
                                        "markets": "spreads", "oddsFormat": "decimal"})
    _track(h)
    res = {}
    for ev in data or []:
        pts = [abs(o.get("point", 0)) for b in ev.get("bookmakers", [])
               for m in b.get("markets", []) for o in m.get("outcomes", [])]
        if pts:
            res[ev["id"]] = sorted(pts)[len(pts) // 2]
    return res


def props(event_id):
    """{(player_norm, stat): {"player", "main": [(book, point, over_px)], "alts": [(book, point, px)]}}"""
    markets = ",".join(m for v in STATS.values() for m in v[:2])
    data, h = get_json(f"{BASE}/events/{event_id}/odds", {"apiKey": ODDS_KEY, "bookmakers": BOOK_PARAM,
                                                          "markets": markets, "oddsFormat": "decimal"})
    _track(h)
    mk2stat = {}
    for stat, v in STATS.items():
        mk2stat[v[0]] = (stat, "main")
        mk2stat[v[1]] = (stat, "alts")
    res = {}
    for b in (data or {}).get("bookmakers", []):
        if b["key"] not in BOOKS:
            continue
        for m in b.get("markets", []):
            if m["key"] not in mk2stat:
                continue
            stat, kind = mk2stat[m["key"]]
            for o in m.get("outcomes", []):
                if o.get("name") != "Over" or o.get("point") is None:
                    continue
                k = (norm(o.get("description", "")), stat)
                rec = res.setdefault(k, {"player": o.get("description", ""), "main": [], "alts": []})
                rec[kind].append((b["key"], float(o["point"]), float(o["price"])))
    return res
