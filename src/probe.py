import json, requests
H = {"User-Agent": "Mozilla/5.0"}
def get(u):
    r = requests.get(u, headers=H, timeout=20); print("\n####", r.status_code, u); return r.json() if r.ok else {}
B = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
gl = get("https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/4278039/gamelog")
print("labels", gl["labels"])
for stp in gl.get("seasonTypes", []):
    print("ST", stp.get("displayName"), [ (c.get("displayName"), c.get("type"), len(c.get("events", []))) for c in stp.get("categories", [])])
    c = stp["categories"][0]; print(" ev0", json.dumps(c["events"][0])[:300])
inj = get(B + "/injuries")
t = inj["injuries"][0]; print("team keys", list(t.keys()), t.get("displayName"))
print(json.dumps(t["injuries"][0])[:900])
st = get("https://site.api.espn.com/apis/v2/sports/basketball/nba/standings")
e = st["children"][0]["standings"]["entries"][0]
print(e["team"]["displayName"], [(s.get("name"), s.get("value")) for s in e["stats"]])
sc = get(f"{B}/teams/1/schedule")
ev = sc["events"][0]; print(json.dumps({k: ev[k] for k in ("id","date")}), ev["competitions"][0]["status"]["type"]["completed"], len(sc["events"]))
sm = get(f"{B}/summary?event=401909939")
p = sm["boxscore"]["players"][0]; s = p["statistics"][0]
print(p["team"]["displayName"], list(s.keys()), s.get("keys") or s.get("labels"))
print(json.dumps(s["athletes"][0])[:500])
print(json.dumps([a for a in s["athletes"] if a.get("didNotPlay")][:1])[:400])
