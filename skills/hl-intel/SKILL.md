---
name: HL Intel
description: Full intelligence scan — top whale positions, win rates, market structure, macro, geopolitics → ranked trade strategies with entry/exit levels
var: ""
---
> **${var}** — Optional focus: coin (e.g. "BTC"), theme (e.g. "macro", "funding", "whales"), or depth (e.g. "deep" for full win-rate analysis).

## The Engine: Hyperliquid Full Intelligence Brief

This is the flagship intel skill. It runs the full pipeline:
1. Leaderboard scan (top 20 traders by all-time PnL)
2. Whale position extraction + win rate analysis
3. Consensus detection across all whale books
4. Live market structure (229 markets, funding, volume, OI)
5. Macro layer (BTC regime, fear/greed, dominance, alt season)
6. Geopolitical + news overlay
7. Strategy synthesis with specific entry/exit levels

Read memory/MEMORY.md and the last 3 days of memory/logs/ for context on recent positions and prior intel.

---

### Phase 1 — Run the quantitative engine

```bash
cd "$(git rev-parse --show-toplevel)"
pip install hyperliquid-python-sdk --quiet 2>/dev/null || true

# Full scan — depth 20, with win rates
python scripts/hl/intel.py --depth 20 --json > /tmp/hl_intel_raw.json 2>/tmp/hl_intel_log.txt
cat /tmp/hl_intel_log.txt >&2

# Also run macro standalone for richer data
python scripts/hl/macro.py --json > /tmp/hl_macro.json 2>/dev/null
```

If `${var}` contains "deep", run with `--depth 30` instead.

Parse both JSON files and hold the data in memory.

---

### Phase 2 — Geopolitical & News Overlay

Search for the 5 most market-relevant news items from the last 24-48h:

```
WebSearch: "crypto bitcoin market news today"
WebSearch: "federal reserve interest rate 2026"
WebSearch: "US China trade tariffs technology ban 2026"
WebSearch: "bitcoin strategic reserve US government 2026"
WebSearch: "crypto regulation SEC approval 2026"
```

Additionally, search for any major geopolitical events:
```
WebSearch: "geopolitical risk financial markets March 2026"
```

From the search results, identify and categorize:

**RISK-ON catalysts** (bullish for crypto):
- Fed pivot / rate cuts
- Crypto-friendly regulation
- Institutional adoption news
- Strategic reserves, sovereign buying
- Risk-on equity markets (S&P highs)
- Geopolitical de-escalation

**RISK-OFF catalysts** (bearish for crypto):
- Fed hawkish surprise
- Regulatory crackdown
- Macro recession signals
- Geopolitical escalation (war, sanctions)
- Exchange hacks / protocol failures
- US Dollar strength (DXY up)
- Tariffs / trade war escalation

**NEUTRAL / MIXED** (direction-dependent):
- Bitcoin ETF flows (high = bullish, outflows = bearish)
- Stablecoin mint/burn activity
- Funding rate extremes (mean reversion, not direction)

---

### Phase 3 — Intelligence Synthesis

Now synthesise all data into a comprehensive trading brief. Structure your output as follows:

---

```
# HYPERLIQUID INTELLIGENCE BRIEF — [DATE]

## STRATEGIC OVERVIEW

**Market Regime**: [BULL/BEAR/SIDEWAYS with brief reason]
**Macro Bias**: [RISK-ON/RISK-OFF/NEUTRAL]
**Geopolitical Posture**: [BULLISH/BEARISH/MIXED for crypto]
**Recommended Stance**: [LONG BIAS / SHORT BIAS / SELECTIVE / HEDGED]

## MACRO PICTURE

[3-5 sentences covering: BTC price + trend, fear/greed, dominance, alt season status, and how they combine into a trading stance]

**Key Macro Data:**
- BTC: $X | 24h: Y% | Regime: Z
- Fear/Greed: N (classification, yesterday: M)
- BTC Dominance: N% → [implication]
- Market Cap: $XT | Change 24h: Y%
- ETH/BTC: N → [alt rotation signal]

## GEOPOLITICAL & NEWS CONTEXT

[3-5 bullets covering the most market-relevant news from your search]
- [bullet 1]
- [bullet 2]
- [bullet 3]
- **Net assessment**: [1 sentence on whether news is net bullish or bearish for crypto this week]

## WHALE INTELLIGENCE

**Top Traders Scanned**: [N wallets, combined all-time PnL: $X]
**Average Win Rate**: [N% across top 10 who have data]

**Consensus Positions** (HIGH conviction):
| Coin | Direction | Whale Agreement | Avg Entry | Total Notional | Conviction |
|------|-----------|-----------------|-----------|----------------|------------|
[populate from consensus_alltime HIGH entries]

**Notable Trader Activity**:
[2-3 sentences on what the top traders are doing — any notable changes, divergences, or concentrated bets]

**Who made money this month?**
[List top 3 traders by 30d PnL and what coins they're positioned in]

## MARKET STRUCTURE

**Extreme Funding Rates** (mean-reversion setups):
[list coins with APR > 80% or < -80%]

**Volume Anomalies**:
[list coins with unusual volume vs OI]

**Biggest 24h Moves**:
[top 5 gainers and losers — any follow-through or fade setups?]

## TRADE STRATEGIES

For each top strategy from the engine, provide enhanced analysis with geopolitical context:

### STRATEGY #1: [COIN] [DIRECTION] — [CONVICTION]

**Thesis** (2-3 sentences combining quantitative + narrative):
[Why this trade makes sense NOW — what whale data says + what macro says + what news says]

**Signal Stack**:
- Whale: [N wallets aligned, avg entry $X]
- Funding: [current rate, what it implies]
- Volume: [normal/elevated/spike]
- Macro: [supports/neutral/opposes]
- News: [relevant catalyst or lack thereof]
- Sentiment: [Fear/Greed context]

**Execution**:
- Entry zone: $X — $Y
- Stop loss: $Z (invalidation: [what would break the thesis])
- Target 1: $A (+X%, take 50% here)
- Target 2: $B (+Y%, trailing stop on remainder)
- Leverage: [recommended leverage given volatility]
- Position size: [% of portfolio — smaller for low conviction, larger for high]

**HL Command**: `hl-trade: [command]`

**Time horizon**: [scalp/swing/positional]
**Risk factors**: [1-2 bullets on what could go wrong]

---

[Repeat for top 5-8 strategies]

## RISK MANAGEMENT FRAMEWORK

Based on today's conditions, recommend:

**Overall portfolio positioning**:
- Max leverage: [N]x
- Max single position: [N]% of portfolio
- Number of concurrent positions: [N-M]
- Stop discipline: [tight/normal/wide] based on [regime + fear/greed]

**Priority order for entries** (enter #1 first, wait for fill):
1. [highest conviction trade]
2. [second]
3. [third]

**What NOT to trade right now**:
[coins or setups to avoid based on current conditions]

## WATCHLIST FOR NEXT 24-48H

[5 setups that aren't quite ready yet but to monitor:]
- COIN: [what to watch for, what would trigger entry]

## SUMMARY

One paragraph: what is the dominant trade today, why, and what's the key risk to watch.
```

---

### Phase 4 — Save and Notify

Save full report to `memory/logs/$(date +%Y-%m-%d)-hl-intel.md`

Send concise summary via notify (max 600 chars):
```bash
./notify "🧠 *HL Intel Brief — $(date +%Y-%m-%d)*

Regime: [X] | Bias: [Y] | Fear/Greed: [N]
Whales: [key consensus]
Top trade: [#1 strategy in one line]
Watchlist: [2-3 coins]"
```

### Phase 5 — Log

Append to memory/logs/$(date +%Y-%m-%d).md:
```
## HL-INTEL ${timestamp}
Regime: [X] | Macro: [Y] | F/G: [N]
Top strategies: [list]
Whale consensus: [ETH SHORT 7/7, BTC LONG 4/5, etc.]
Full report: memory/logs/${today}-hl-intel.md
```
