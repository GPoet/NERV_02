---
name: HL Monitor
description: Monitor open Hyperliquid positions — PnL, liquidation risk, funding costs, margin health
var: ""
---
> **${var}** — Optional coin filter. If empty, monitors all open positions.

## Radar: Hyperliquid Position Monitor

Requires `HL_WALLET_ADDRESS` secret (and optionally `HL_PRIVATE_KEY`).

Read memory/MEMORY.md and the last 2 days of memory/logs/ for baseline context.

### Step 1 — Install dependencies
```bash
pip install hyperliquid-python-sdk --quiet 2>/dev/null || true
```

### Step 2 — Fetch current position state
```bash
cd "$(git rev-parse --show-toplevel)"
python scripts/hl/monitor.py --json > /tmp/hl_monitor.json
cat /tmp/hl_monitor.json
```

### Step 3 — Assess risk and generate alerts

Parse the JSON and evaluate:

**CRITICAL alerts** (notify immediately):
- Any position with `liq_distance_pct < 10%`
- `margin_utilization_pct > 80%`
- Any position `pnl_pct < -30%`

**WARNING alerts** (include in notification):
- `liq_distance_pct < 20%`
- `margin_utilization_pct > 60%`
- Open order count > 20 (possible order bloat)
- Funding rate on open position > 0.1% per 8h (funding drain)

**INFO** (include in daily summary):
- Largest winning/losing position
- Net funding income/expense for the week
- Margin efficiency (PnL per dollar of margin)

### Step 4 — Notify

Determine urgency:
- **CRITICAL**: notify immediately with full details
- **WARNING**: include in normal notification
- **OK**: brief confirmation only

```bash
./notify "*HL Monitor — $(date +%Y-%m-%d %H:%M)*

$(cat /tmp/hl_alert.txt)"
```

Write alert text to /tmp/hl_alert.txt.

### Step 5 — Log

Append to memory/logs/$(date +%Y-%m-%d).md:
```
## HL-MONITOR ${timestamp}
Status: [OK/WARNING/CRITICAL]
Positions: N open | Account: $X | PnL: $Y
Flags: [any flagged positions]
```

If no positions open, log "HL_MONITOR_NO_POSITIONS" and end.
