import re
import time
import unicodedata
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests

from .config import TZ

HEADERS = {"User-Agent": "Mozilla/5.0 (nba-props-agent)"}
SYD = ZoneInfo(TZ)
ET = ZoneInfo("America/New_York")


def get_json(url, params=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                return r.json(), r.headers
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (i + 1))
                continue
            print(f"GET {url.split('?')[0]} -> {r.status_code}")
            return None, r.headers
        except requests.RequestException as e:
            print(f"GET error {e}")
            time.sleep(2 * (i + 1))
    return None, {}


def norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", "", s.replace("-", " "))
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return " ".join(s.split())


def parse_ts(s):
    s = s.replace("Z", "+00:00")
    if re.search(r"T\d\d:\d\d\+", s):
        s = s.replace("+", ":00+", 1)
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def now_utc():
    return datetime.now(timezone.utc)


def syd_date(dt=None):
    return (dt or now_utc()).astimezone(SYD).date()


def et_date(dt):
    return dt.astimezone(ET).date()
