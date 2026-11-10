"""Free ESPN feeds: rosters, game logs, injuries, schedules, standings, box scores."""
import time
from .util import get_json, norm, parse_ts

B = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
GL = "https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{}/gamelog"
STAND = "https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"
TEAM_ALIAS = {"la clippers": "los angeles clippers"}


def tkey(name):
    n = norm(name)
    return TEAM_ALIAS.get(n, n)


class Espn:
    def __init__(self):
        self._c = {}

    def _get(self, url):
        if url not in self._c:
            data, _ = get_json(url)
            self._c[url] = data
            time.sleep(0.05)
        return self._c[url]

    def scoreboard(self, d):
        data = self._get(f"{B}/scoreboard?dates={d:%Y%m%d}") or {}
        games = []
        for ev in data.get("events", []):
            comp = ev["competitions"][0]
            t = {c["homeAway"]: c["team"] for c in comp["competitors"]}
            games.append({"id": ev["id"], "home_id": t["home"]["id"], "away_id": t["away"]["id"],
                          "home": tkey(t["home"]["displayName"]), "away": tkey(t["away"]["displayName"])})
        return games

    def roster(self, team_id):
        data = self._get(f"{B}/teams/{team_id}/roster") or {}
        return {norm(a["displayName"]): a["id"] for a in data.get("athletes", [])}

    def gamelog(self, athlete_id):
        """Regular-season games this season, newest first."""
        data = self._get(GL.format(athlete_id)) or {}
        labels = data.get("labels", [])
        if not labels:
            return []
        idx = {k: labels.index(k) for k in ("MIN", "PTS", "REB", "AST") if k in labels}
        meta = data.get("events", {})
        out, seen = [], set()
        for st in data.get("seasonTypes", [])[:2]:
            if "Regular Season" not in st.get("displayName", ""):
                continue
            for cat in st.get("categories", []):
                for e in cat.get("events", []):
                    eid = e["eventId"]
                    if eid in seen or eid not in meta:
                        continue
                    seen.add(eid)
                    s = e["stats"]
                    try:
                        g = {k.lower(): float(s[i]) for k, i in idx.items()}
                    except (ValueError, IndexError):
                        continue
                    m = meta[eid]
                    g.update({"event_id": eid, "date": parse_ts(m["gameDate"]),
                              "home": m.get("atVs") == "vs", "opp_id": str(m.get("opponent", {}).get("id"))})
                    out.append(g)
            break
        out.sort(key=lambda g: g["date"], reverse=True)
        return out

    def injuries(self):
        data = self._get(f"{B}/injuries") or {}
        res = {}
        for team in data.get("injuries", []):
            for inj in team.get("injuries", []):
                res[norm(inj["athlete"]["displayName"])] = {
                    "status": inj.get("status", ""), "team": tkey(team.get("displayName", "")),
                    "name": inj["athlete"]["displayName"],
                    "comment": (inj.get("shortComment", "") + " " + inj.get("longComment", "")).lower()}
        return res

    def standings(self):
        data = self._get(STAND) or {}
        res = {}
        for conf in data.get("children", []):
            for e in conf.get("standings", {}).get("entries", []):
                s = {x.get("name"): x.get("value") for x in e.get("stats", [])}
                if s.get("avgPointsFor"):
                    res[tkey(e["team"]["displayName"])] = (s["avgPointsFor"], s["avgPointsAgainst"])
        return res

    def team_games(self, team_id):
        """Completed games: list of (event_id, utc datetime), oldest first."""
        data = self._get(f"{B}/teams/{team_id}/schedule") or {}
        out = []
        for ev in data.get("events", []):
            if ev["competitions"][0]["status"]["type"].get("completed"):
                out.append((ev["id"], parse_ts(ev["date"])))
        return sorted(out, key=lambda x: x[1])

    def box(self, event_id):
        """Returns (completed, {player_norm: {pts, reb, ast, dnp}})."""
        data, _ = get_json(f"{B}/summary?event={event_id}")
        if not data:
            return False, {}
        try:
            completed = data["header"]["competitions"][0]["status"]["type"]["completed"]
        except (KeyError, IndexError):
            completed = False
        players = {}
        for team in data.get("boxscore", {}).get("players", []):
            for s in team.get("statistics", [])[:1]:
                keys = s.get("keys", [])
                for a in s.get("athletes", []):
                    nm = norm(a["athlete"]["displayName"])
                    st = a.get("stats") or []
                    if a.get("didNotPlay") or not st:
                        players[nm] = {"dnp": True}
                        continue
                    row = dict(zip(keys, st))
                    try:
                        players[nm] = {"dnp": False, "points": float(row.get("points", 0)),
                                       "rebounds": float(row.get("rebounds", 0)),
                                       "assists": float(row.get("assists", 0))}
                    except ValueError:
                        players[nm] = {"dnp": True}
        return completed, players
