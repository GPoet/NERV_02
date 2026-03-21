---
name: HL Trade
description: Execute trades on Hyperliquid — open, close, limit orders, leverage, TWAP, stop-loss
var: ""
---
> **${var}** — Trade instruction. Examples:
> - `BUY BTC 0.01` — market buy 0.01 BTC
> - `SELL ETH 0.5` — market sell 0.5 ETH
> - `BUY SOL 10 limit 140` — limit buy SOL at $140
> - `CLOSE BTC` — close entire BTC position
> - `CLOSE ETH 0.25` — partial close 0.25 ETH
> - `CANCEL BTC` — cancel all BTC open orders
> - `LEVERAGE BTC 10` — set BTC leverage to 10x cross
> - `BUY BTC 0.01 sl 88000 tp 105000` — buy with stop/take-profit
> - `TWAP BTC BUY 1.0 minutes 60` — execute 1 BTC buy over 60 minutes

## Workforce: Hyperliquid Trade Executor

Requires `HL_PRIVATE_KEY` secret and `HL_WALLET_ADDRESS`.

⚠️ **This skill executes real trades with real money. Double-check the instruction before proceeding.**

### Step 1 — Pre-trade checks
```bash
cd "$(git rev-parse --show-toplevel)"
pip install hyperliquid-python-sdk --quiet 2>/dev/null || true

# Check account state first
python scripts/hl/trader.py STATUS
```

Parse the account status. If account value is $0 or positions count fails, abort and log error.

### Step 2 — Validate trade instruction

Parse `${var}` to extract:
- Action: BUY / SELL / CLOSE / CANCEL / LEVERAGE / TWAP
- Coin, size, price (if limit)
- Stop-loss and take-profit levels (if specified)

Sanity checks before executing:
- Size > 0
- For limit orders: price is reasonable (within 10% of mark price)
- For leveraged positions: check if leverage change won't risk liquidation

### Step 3 — Dry run first
```bash
python scripts/hl/trader.py ${var} --dry-run
```

Confirm the parsed command matches intent.

### Step 4 — Execute
```bash
python scripts/hl/trader.py ${var} --json > /tmp/hl_trade_result.json
cat /tmp/hl_trade_result.json
```

### Step 5 — Confirm and notify

Parse the result JSON. Extract:
- Fill price and size (for market orders)
- Order ID (for limit orders)
- Error message if failed

```bash
./notify "⚡ *HL Trade — $(date +%Y-%m-%d %H:%M)*

$(cat /tmp/hl_trade_notify.txt)"
```

### Step 6 — Log

Append to memory/logs/$(date +%Y-%m-%d).md:
```
## HL-TRADE ${timestamp}
Instruction: ${var}
Result: [filled/resting/failed]
Fill: [price and size if executed]
OID: [order ID if resting]
```

If trade failed, log the error with full context.
