import csv
import json
import os
from .config import DATA_DIR

PICK_COLS = ["pick_id", "date", "run", "n", "type", "legs", "odds_event_id", "espn_event_id", "game", "tip_utc",
             "player", "stat", "line", "book", "odds", "edge", "model_p", "mu", "ref_line", "ref_odds", "hits10",
             "stake", "flags", "status", "dry_run", "result", "actual"]
BET_COLS = ["bet_id", "date", "pick_id", "type", "description", "book", "odds", "stake", "qualified",
            "status", "result", "pl", "placed_utc"]


def _path(name):
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, name)


def read(name, cols):
    p = _path(name)
    if not os.path.exists(p):
        return []
    with open(p, newline="") as f:
        return [{c: r.get(c, "") for c in cols} for r in csv.DictReader(f)]


def write(name, cols, rows):
    with open(_path(name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


def picks():
    return read("picks.csv", PICK_COLS)


def save_picks(rows):
    write("picks.csv", PICK_COLS, rows)


def bets():
    return read("ledger.csv", BET_COLS)


def save_bets(rows):
    write("ledger.csv", BET_COLS, rows)


def state():
    p = _path("state.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"tg_offset": 0}


def save_state(s):
    with open(_path("state.json"), "w") as f:
        json.dump(s, f, indent=1)
