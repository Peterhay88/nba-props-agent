import json, requests
H = {"User-Agent": "Mozilla/5.0"}
def get(u):
    r = requests.get(u, headers=H, timeout=20); print("\n####", r.status_code, u); return r.json() if r.ok else {}
def show(o, d=0, maxd=4, maxl=3):
    pad = "  " * d
    if d > maxd: return
    if isinstance(o, dict):
        for k, v in list(o.items())[:25]:
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}: {type(v).__name__}({len(v)})"); show(v, d+1, maxd, maxl)
            else: print(f"{pad}{k}: {str(v)[:80]}")
    elif isinstance(o, list):
        for v in o[:maxl]: show(v, d+1, maxd, maxl) if isinstance(v,(dict,list)) else print(f"{pad}- {str(v)[:80]}")
B = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
sb = get(B + "/scoreboard"); ev = sb["events"][0]
print(ev["id"], ev["date"], [ (c["homeAway"], c["team"]["id"], c["team"]["displayName"]) for c in ev["competitions"][0]["competitors"]])
tid = ev["competitions"][0]["competitors"][0]["team"]["id"]
ro = get(f"{B}/teams/{tid}/roster"); a = ro["athletes"][0]; print("roster athlete keys", list(a.keys())[:15], a.get("id"), a.get("displayName"))
gl = get(f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{a['id']}/gamelog"); show(gl, maxd=5)
inj = get(B + "/injuries"); show(inj, maxd=4, maxl=2)
st = get("https://site.api.espn.com/apis/v2/sports/basketball/nba/standings"); show(st, maxd=6, maxl=1)
sc = get(f"{B}/teams/{tid}/schedule"); show(sc, maxd=4, maxl=1)
done = [e for e in sc.get("events", []) if e["competitions"][0]["status"]["type"]["completed"]]
if done:
    sm = get(f"{B}/summary?event={done[-1]['id']}"); show(sm.get("boxscore", {}), maxd=6, maxl=2)
