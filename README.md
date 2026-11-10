# NBA props agent

Scans Sportsbet, Neds and TAB NBA player props (points, rebounds, assists), finds alternate lines at $1.30-$1.60 with
a 3%+ edge, and sends picks to Telegram. Every rule in `BETTING_RULEBOOK.md` is enforced in `agent/rules.py` and
`agent/config.py`.

## Schedule (Sydney time)
- 10:00 main scan (`Scan` workflow)
- 12:00 and 13:15 update scans: only on when the repo variable `FULL_SCHEDULE` = `true` (needs the paid odds plan)
- Every 20 min 10:00-19:00: `Sync` records your Telegram taps and settles finished games

## Test mode
Repo variable `DRY_RUN` (Settings > Secrets and variables > Actions > Variables). Unset or `true` = picks are marked
TEST with no buttons and are still graded. Set to `false` to go live.

## Telegram commands
- Tap **Placed** or **Skip** under each pick
- `/b365 N ODDS` placed pick N at Bet365
- `/placed N [ODDS] [STAKE]` placed pick N at a different price or stake
- `/bet STAKE ODDS description` a bet the agent didn't pick (logged as a breach)
- `/settle BETID win|loss|void` settle a manual bet
- `/status` bankroll and limits

## Data
`data/picks.csv` every pick (graded after games) · `data/ledger.csv` bets you placed · `data/state.json`
