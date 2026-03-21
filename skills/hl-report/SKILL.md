---
name: HL Report
description: Generate a comprehensive Hyperliquid portfolio report — positions, PnL, funding, recent trades
var: ""
---
> **${var}** — Optional period override: `daily` (default) or `weekly`.

## Broadcast: Hyperliquid Portfolio Report

Requires `HL_WALLET_ADDRESS` secret.

Read memory/MEMORY.md and the last 7 days of memory/logs/ for historical context and PnL trend.

### Step 1 — Install and run
```bash
cd "$(git rev-parse --show-toplevel)"
pip install hyperliquid-python-sdk --quiet 2>/dev/null || true
python scripts/hl/report.py --json > /tmp/hl_report.json
cat /tmp/hl_report.json
```

### Step 2 — Generate report narrative

From the JSON, produce a markdown report that includes:

**Header**: Date, portfolio value, total PnL change
**Position summary table**: All open positions with size, notional, PnL%, leverage, liq distance
**PnL breakdown**:
  - Unrealized PnL (all positions)
  - Realized PnL (24h)
  - Net funding (7d) — is the account earning or paying funding?
  - Fees paid (24h)
**Risk section**:
  - Overall margin utilization
  - Most exposed position (closest to liquidation)
  - Largest single position as % of portfolio
**Recent activity**: Last 10 fills with timestamps
**Insight**: 2-3 sentences of your analysis — what's working, what's at risk, any action items

### Step 3 — Save report

Save the full report to memory/logs/$(date +%Y-%m-%d)-hl-report.md.

### Step 4 — Notify with summary

Send a concise summary (max 500 chars) via notify:
```bash
./notify "*HL Portfolio Report — $(date +%Y-%m-%d)*

Portfolio: \$X | PnL: ±\$Y
Positions: N open | Largest: COIN (X%)
7d Funding: ±\$Z
[Key insight or alert]"
```

### Step 5 — Log

Append to memory/logs/$(date +%Y-%m-%d).md:
```
## HL-REPORT ${timestamp}
Portfolio: $X | Unrealized: $Y | 7d Funding: $Z
Positions: N
Full report: memory/logs/${today}-hl-report.md
```
