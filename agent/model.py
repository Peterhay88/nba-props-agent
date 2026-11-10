"""Projection + probability. Simple, transparent, and graded every day by the ledger."""
import math
from statistics import NormalDist

USAGE_BUMP = {"pts": 1.06, "ast": 1.05, "reb": 1.03}


def _wmean(xs, ws):
    return sum(x * w for x, w in zip(xs, ws)) / sum(ws)


def project(games, stat, is_home, opp_def, pace, teammate_out):
    """games: this season, newest first. Returns (mu, sigma, last10_values, flags)."""
    last = [g[stat] for g in games[:10]]
    ws = ([2] * 5 + [1] * 5)[:len(last)]          # last 5 games count double
    mu = _wmean(last, ws)
    flags = []
    season = [g[stat] for g in games]
    home = [g[stat] for g in games if g["home"]]
    away = [g[stat] for g in games if not g["home"]]
    overall = sum(season) / len(season) if season else 0
    if overall > 0 and len(home) >= 4 and len(away) >= 4:
        venue = home if is_home else away
        r = (sum(venue) / len(venue)) / overall
        if abs(r - 1) >= 0.08:
            mu *= 1 + 0.5 * (r - 1)
            flags.append(f"{'Home' if is_home else 'Away'} split {100 * (r - 1):+.0f}%")
    factor = opp_def if stat == "pts" else pace
    if factor:
        adj = 1 + 0.5 * (factor - 1)
        mu *= adj
        if abs(adj - 1) >= 0.03:
            label = "Soft matchup" if adj > 1 else "Tough matchup"
            flags.append(f"{label} {100 * (adj - 1):+.0f}%")
    if teammate_out:
        mu *= USAGE_BUMP[stat]
        flags.append(f"{teammate_out} out, usage up")
    var = _wmean([(x - _wmean(last, ws)) ** 2 for x in last], ws)
    sd = math.sqrt(var)
    floor = max(0.22 * mu, 2.0) if stat == "pts" else max(0.9 * math.sqrt(max(mu, 0.1)), 1.0)
    return mu, max(sd, floor), last, flags


def prob_over(line, mu, sigma, last):
    model = 1 - NormalDist(mu, sigma).cdf(line)
    hits = sum(1 for x in last if x > line)
    emp = (hits + 1) / (len(last) + 2)
    return min(0.65 * model + 0.35 * emp, 0.90), hits
