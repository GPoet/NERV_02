---
name: HL Alpha
description: Synthesise trade ideas from market data + news + on-chain signals + sentiment into actionable HL setups
var: ""
---
> **${var}** — Optional focus: coin symbol (e.g. "BTC") or theme (e.g. "funding", "momentum", "narrative").

## The Engine: Hyperliquid Alpha Synthesis

This skill is the intelligence core — it aggregates signals from every available source, then reasons over them to produce ranked, specific trade ideas for Hyperliquid.

Read memory/MEMORY.md for current tracked coins and active theses.

---

### Phase 1 — Market Structure (Hyperliquid data)

```bash
cd "$(git rev-parse --show-toplevel)"
pip install hyperliquid-python-sdk --quiet 2>/dev/null || true

# Full market scan — get all signals
python scripts/hl/scanner.py --top 20 --json > /tmp/hl_alpha_market.json
```

Extract and note:
- Top 5 coins by opportunity score
- Extreme funding rate plays (absolute APR > 100%)
- Volume spikes (vol/OI > 1.5x)
- Biggest movers (up AND down — fade candidates)

If `${var}` targets a specific coin, also fetch its order book depth:
```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from hl.client import get_l2_book, get_candles
import json, time
coin = '${var}'.upper() if '${var}' else 'BTC'
book = get_l2_book(coin)
# Get 4h candles for last 30 days
candles = get_candles(coin, '4h', int(time.time()*1000) - 30*24*3600*1000)
print(json.dumps({'book': book, 'candles_4h_count': len(candles), 'recent_candles': candles[-5:]}))
" > /tmp/hl_alpha_depth.json 2>/dev/null
```

---

### Phase 2 — News & Narrative Intel

Read the relevant skill files and execute their core data-fetching steps:

**Crypto news** (from RSS):
Read skills/rss-digest/SKILL.md and execute Step 1 only (fetch headlines, don't send notification).
Focus on: exchange news, protocol upgrades, regulatory moves, macro events.

**Hacker News** (tech/AI angle):
Read skills/hacker-news-digest/SKILL.md and execute fetch step.
Note any AI/infrastructure/DePIN narratives that could affect crypto.

**Search for targeted intel**:
```
WebSearch: "hyperliquid ${var} trading" site:twitter.com OR site:x.com latest
WebSearch: "${var} crypto news March 2026"
WebSearch: "crypto derivatives funding rate analysis 2026"
```

---

### Phase 3 — On-Chain Signals

Check whale/smart money activity:
```
WebFetch: https://api.coingecko.com/api/v3/global — get market-wide metrics
WebSearch: "large whale ${var} on-chain movement 2026"
```

For context on open interest across venues:
```
WebSearch: "bitcoin open interest derivatives 2026 analysis"
```

---

### Phase 4 — Sentiment Check

```
WebSearch: "crypto fear greed index today"
WebSearch: "hyperliquid liquidations today"
```

Note: extreme fear + extreme negative funding = high-probability long setup.
Extreme greed + extreme positive funding = high-probability short setup or exit.

---

### Phase 5 — Alpha Synthesis

Now synthesise everything into **3-5 ranked trade ideas**.

For each idea, produce:

```
### IDEA #N: [COIN] [LONG/SHORT]

**Conviction**: HIGH / MEDIUM / LOW
**Timeframe**: scalp (< 4h) / swing (1-7d) / positional (2-4w)

**Thesis** (2-3 sentences):
Why this trade makes sense right now, combining market data + news + sentiment.

**Entry Zone**: $X — $Y
**Stop Loss**: $Z (X% from entry)
**Target 1**: $A (+X%)
**Target 2**: $B (+Y%)
**Invalidation**: [price level or event that kills the thesis]

**Supporting signals**:
- Market: [funding rate, OI, volume data]
- News: [relevant headlines]
- Sentiment: [fear/greed, social signal]
- Risk: [key risks to this trade]

**HL Execution**:
`hl-trade: BUY/SELL COIN SIZE [limit PRICE] [sl STOP] [tp TARGET]`
```

Rank ideas 1-N by conviction × risk/reward.

---

### Phase 6 — Risk Assessment

Before finalising, check:
- Are any ideas correlated? (multiple BTC-correlated longs = not diversified)
- Is the portfolio currently overleveraged? (run hl-monitor first if recent data not in logs)
- Does any idea conflict with existing positions? (don't add to a losing position)

---

### Phase 7 — Output & Notify

Save full alpha report to memory/logs/$(date +%Y-%m-%d)-hl-alpha.md.

Send top 3 ideas via notify (max 600 chars):
```bash
./notify "🧠 *HL Alpha — $(date +%Y-%m-%d)*

#1 [COIN] [LONG/SHORT]: one-line thesis | Entry $X | Stop $Y | Target $Z
#2 [COIN] [LONG/SHORT]: one-line thesis | Entry $X | Stop $Y | Target $Z
#3 [COIN] [LONG/SHORT]: one-line thesis | Entry $X | Stop $Y | Target $Z

Fear/Greed: [index]"
```

### Step 8 — Log

Append to memory/logs/$(date +%Y-%m-%d).md:
```
## HL-ALPHA ${timestamp}
Ideas generated: N
Top idea: [coin side] — [one line thesis]
Full report: memory/logs/${today}-hl-alpha.md
```
