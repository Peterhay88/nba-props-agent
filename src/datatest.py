"""Step 1 data test: checks what NBA player props and alt lines TheOddsAPI
returns for Australian bookmakers, and confirms the Telegram bot works.
Costs roughly 12 odds credits (2 games x 6 markets x 1 region)."""
import os
import sys
import requests

ODDS_KEY = os.environ["ODDS_API_KEY"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]
BASE = "https://api.the-odds-api.com/v4/sports/basketball_nba"
MARKETS = [
    "player_points", "player_rebounds", "player_assists",
    "player_points_alternate", "player_rebounds_alternate", "player_assists_alternate",
]
WANTED_BOOKS = {"sportsbet", "neds", "tab", "ladbrokes_au", "betr_au", "pointsbetau", "unibet"}


def telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": text},
        timeout=20,
    )
    print("Telegram:", "OK" if r.ok else f"FAILED {r.status_code} {r.text[:200]}")
    return r.ok


def main():
    lines = []
    events = requests.get(f"{BASE}/events", params={"apiKey": ODDS_KEY}, timeout=20)
    if not events.ok:
        msg = f"Odds API error {events.status_code}: {events.text[:200]}"
        print(msg)
        telegram("Props agent data test: " + msg)
        sys.exit(1)
    evs = events.json()
    lines.append(f"NBA events listed: {len(evs)}")
    remaining = None
    for ev in evs[:2]:
        name = f"{ev['away_team']} @ {ev['home_team']}"
        r = requests.get(
            f"{BASE}/events/{ev['id']}/odds",
            params={"apiKey": ODDS_KEY, "regions": "au", "markets": ",".join(MARKETS),
                    "oddsFormat": "decimal"},
            timeout=30,
        )
        remaining = r.headers.get("x-requests-remaining", remaining)
        if not r.ok:
            lines.append(f"\n{name}: error {r.status_code} {r.text[:150]}")
            continue
        data = r.json()
        lines.append(f"\n{name}")
        books = data.get("bookmakers", [])
        if not books:
            lines.append("  No AU bookmaker props returned")
        for b in books:
            mk = {m["key"]: m["outcomes"] for m in b.get("markets", [])}
            flag = "" if b["key"] in WANTED_BOOKS else " (other)"
            summary = ", ".join(f"{k.replace('player_', '')}:{len(v)}" for k, v in mk.items())
            lines.append(f"  {b['title']}{flag} -> {summary or 'no prop markets'}")
            alt = mk.get("player_rebounds_alternate") or mk.get("player_points_alternate")
            if alt:
                o = alt[0]
                lines.append(f"    e.g. {o.get('description')} {o['name']} {o.get('point')} @ {o['price']}")
    lines.append(f"\nOdds credits remaining: {remaining}")
    report = "Props agent data test\n" + "\n".join(lines)
    print(report)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as f:
            f.write("```\n" + report + "\n```\n")
    telegram(report[:4000])


if __name__ == "__main__":
    main()
