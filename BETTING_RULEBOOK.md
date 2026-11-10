# Peter's Betting Rulebook — NBA Player Props
Version 1.0 · 10 Nov 2026

These rules are not up for debate mid-session. They change only at the Sunday review, in writing, never on game day.

---

## 1. Bankroll
- **Starting bankroll:** $5,000, held only for betting and kept separate from personal and business money.
- **No top-ups mid-week.** Money only goes in at the Sunday review.
- **Drawdown checkpoint:** if the bankroll falls to **$3,500**, betting stops until a full review of the ledger is done. Nothing gets reloaded to "win it back".

## 2. Stakes
- **Standard bet: 5% of the week's starting bankroll** ($250 on $5k).
- **Max bet: 10%** ($500). Only for the top tier: the agent's edge is **≥ 8% on the actual line taken** AND minutes and injury status are confirmed.
- **2-leg multi: max 5%**, whatever the confidence.
- Stakes are set from the **Monday bankroll** and fixed for the week. They don't change after a win or a loss.

## 3. Loss limits
- **Daily stop: $500.** Once day losses hit $500, betting is done for the day. No exceptions, no "one more".
- **Weekly stop: $1,000** (Mon–Sun). Once hit, no more bets until Monday.
- **Max 4 bets per day**, multis included.

## 4. What counts as a qualified bet
A selection can be bet ONLY if the agent has flagged it as qualified, which means all of these are true:
1. **Market:** NBA player points, rebounds or assists, over/under.
2. **Odds:** **$1.30 to $1.60**.
3. **Edge recalculated on the line actually bet.** If the agent found value on Over 4.5 rebounds @ $1.90 and the bet is Over 3.5 @ $1.40, the edge must be worked out again for Over 3.5. It cannot carry over from the main line. Alt lines usually carry a bigger bookie margin.
4. **Minimum edge: 3%** on that line (model probability × odds − 1 ≥ 0.03).
5. **Player status confirmed:** not listed out or questionable, and projected minutes are in line with the season average.
6. **Best price taken** across Sportsbet, Neds and TAB (scanned automatically). Bet365 is checked manually against the agent's picks, and a better Bet365 price is logged via Telegram.

If it's not on the agent's qualified list, it doesn't get bet. Hunches, tips and "looks good" bets are banned.

## 5. Multis
- **Max 2 legs.** Never 3+.
- **Both legs must be qualified on their own** (Section 4).
- **Different games only.** Same-game legs move together, so they aren't two independent edges.
- A multi uses up one of the 4 daily bets.

## 6. The ledger (every bet, no exceptions)
Log for each bet: date, game, player, market, line, bookie, odds, stake, agent edge %, qualified Y/N, result, P/L, running bankroll.
- Results are logged after games finish, every day.
- **Any bet not on the qualified list is logged as a BREACH**, win or lose.

## 7. Breaches
- **1 breach** in a week: the next day is a no-bet day.
- **2 breaches** in a week: no betting until Monday.
- Winning breaches count. A winning breach just reinforces the habit that loses.

## 8. Sunday review (15 minutes)
- Weekly P/L, hit rate and average odds.
- Hit rate against the break-even rate for the odds taken (e.g. $1.40 needs 71.4%).
- Compare actual results to the agent's predicted edge to check whether its edges are real.
- Breaches.
- Any rule change is decided here, written here, and starts Monday.

## 9. Proof before scaling
- Nothing about stakes goes up until **100+ logged qualified bets** show a profit **and** a hit rate above break-even.
- If the agent's edges don't show up in actual results after 100 bets, fix the model before betting more.

## 10. Backstop
- Set **deposit limits at each bookie** that match this bankroll. That limit still holds when willpower doesn't.

---

## 11. Scanner spec (how the agent qualifies a bet)
- **Form:** weighted to the last 5–10 games. Add the home/away split when the player has a clear trend.
- **Minutes:** no minimum. **Skip** any player on, or just coming off, a minutes restriction.
- **Usage bump:** when a prominent teammate is ruled out, adjust the player's projection up.
- **Matchup:** factor in what the opponent allows to that position, and game pace.
- **Auto-skip:** second night of a back-to-back, likely blowouts (starters sit the 4th), players returning from injury, the last few weeks of the regular season.
- **Alt lines:** no limit on how far below the main line it goes. It drops as far as needed to land in $1.30–$1.60, then must still clear the 3% edge on that exact line.
- **Run times (Sydney):** 10:00 full scan · 12:00 re-check · 13:30 final check for late games. The 12:00 and 13:30 runs only message when something changes (new qualifier, pick withdrawn, odds out of range).
- **Outputs:** phone message per run, plus a dashboard (bankroll, limits used, today's picks, ledger, predicted-vs-actual edge).
- **Results:** logged automatically after games finish.
