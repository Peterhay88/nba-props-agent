"""All rulebook numbers live here. Change them only at the Sunday review."""
import os

BANKROLL_START = 5000.0
STAKE_STD = 0.05          # standard bet: 5% of Monday bankroll
STAKE_MAX = 0.10          # top tier only
STAKE_MULTI = 0.05        # 2-leg multi
TOP_TIER_EDGE = 0.08
MIN_EDGE = 0.03
ODDS_MIN, ODDS_MAX = 1.30, 1.60
DAY_STOP = 500.0
WEEK_STOP = 1000.0
MAX_BETS_DAY = 4
DRAWDOWN_FLOOR = 3500.0
MIN_STAKE = 50.0
# Shrink the model toward the bookie's own price: small samples overstate edges.
MARKET_WEIGHT = 0.5      # 50% model, 50% market
ALT_MARGIN = 0.06        # assumed bookie margin on alternate lines

BOOKS = {"sportsbet": "Sportsbet", "neds": "Neds", "tab": "TAB"}
# stat -> (main market, alt market, ESPN gamelog label, ESPN box key)
STATS = {
    "pts": ("player_points", "player_points_alternate", "PTS", "points"),
    "reb": ("player_rebounds", "player_rebounds_alternate", "REB", "rebounds"),
    "ast": ("player_assists", "player_assists_alternate", "AST", "assists"),
}
STAT_NAME = {"pts": "pts", "reb": "reb", "ast": "ast"}

SEASON_END_SKIP = "2027-03-29"   # skip the last few weeks of the regular season
BLOWOUT_SPREAD = 12.5            # skip games with a spread this big or bigger
MIN_GAMES = 6                    # need this many games this season
SLATE_HOURS = 16                 # games tipping within this many hours count as today's slate

TZ = "Australia/Sydney"
DRY_RUN = os.environ.get("DRY_RUN", "true").strip().lower() != "false"
ODDS_KEY = os.environ.get("ODDS_API_KEY", "")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
