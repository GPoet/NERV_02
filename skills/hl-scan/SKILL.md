---
name: HL Scan
description: Scan all Hyperliquid perpetuals for high-conviction setups — funding extremes, volume spikes, price momentum
var: ""
---
> **${var}** — Optional coin filter (e.g. "BTC"). If empty, scans all markets.

## Eagle Eye: Hyperliquid Market Scanner

Read memory/MEMORY.md and the last 2 days of memory/logs/ for recent HL context.

### Step 1 — Install dependencies
```bash
pip install hyperliquid-python-sdk --quiet 2>/dev/null || true
```

### Step 2 — Run the scanner
```bash
cd "$(git rev-parse --show-toplevel)"
python scripts/hl/scanner.py --top 15 --json > /tmp/hl_scan.json
cat /tmp/hl_scan.json
```

If the JSON output contains errors, diagnose and retry once.

### Step 3 — Analyse the results

Parse the JSON and extract:
- **Top 3 trade ideas** with clear reasoning (which direction, why, what to watch)
- **Extreme funding plays**: coins where funding APR > 100% or < -100% = mean reversion setups
- **Volume anomalies**: coins with vol/OI ratio > 2x = unusual positioning
- **Momentum plays**: biggest 24h movers that could continue or reverse

For each trade idea, provide:
- Coin and direction (long/short)
- Key thesis in 1-2 sentences
- Entry zone, invalidation level
- Expected timeframe

### Step 4 — Notify

```bash
./notify "🎯 *HL Scan — $(date +%Y-%m-%d)*

$(cat /tmp/hl_scan_summary.txt)"
```

Write a concise summary (max 400 chars) to /tmp/hl_scan_summary.txt before notifying.

### Step 5 — Log

Append results to memory/logs/$(date +%Y-%m-%d).md:
```
## HL-SCAN ${timestamp}
Top setups: [coin1 LONG/SHORT, coin2 LONG/SHORT, coin3 LONG/SHORT]
Extreme funding: [coins at extremes]
Full scan: /tmp/hl_scan.json
```
