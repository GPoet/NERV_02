#!/usr/bin/env python3
"""
hl_report.py — Hyperliquid portfolio report.

Generates a comprehensive daily/weekly portfolio summary:
  - Account value, PnL, margin usage
  - All open positions with detailed metrics
  - 7-day funding income/expense
  - Recent fills (last 24h)
  - Fee tier status

Usage:
    HL_WALLET_ADDRESS=0x... python report.py [--json]
"""
import sys
import json
import time
import argparse
from datetime import datetime, timezone

import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.dirname(_here))
from hl.client import (
    get_clearinghouse_state, get_spot_state,
    get_user_fills, get_user_fees, get_user_funding,
    get_meta_and_asset_ctxs, wallet_address,
)

MS_24H = 24 * 3600 * 1000
MS_7D  = 7  * 24 * 3600 * 1000
MS_30D = 30 * 24 * 3600 * 1000


def ts_to_str(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def run_report(address: str) -> dict:
    now_ms = int(time.time() * 1000)

    # Perp state
    state = get_clearinghouse_state(address)
    ms = state.get("marginSummary", {})

    # Mark prices
    try:
        meta_ctxs = get_meta_and_asset_ctxs()
        universe = meta_ctxs[0]["universe"]
        ctxs = meta_ctxs[1]
        mark_prices = {
            universe[i]["name"]: float(ctxs[i].get("markPx", 0))
            for i in range(min(len(universe), len(ctxs)))
            if ctxs[i]
        }
        funding_rates = {
            universe[i]["name"]: float(ctxs[i].get("funding", 0))
            for i in range(min(len(universe), len(ctxs)))
            if ctxs[i]
        }
    except Exception:
        mark_prices = {}
        funding_rates = {}

    # Spot balances
    try:
        spot_state = get_spot_state(address)
        spot_balances = spot_state.get("balances", [])
    except Exception:
        spot_balances = []

    # Recent fills (24h)
    try:
        fills = get_user_fills(address)
        fills_24h = [f for f in fills if now_ms - int(f.get("time", 0)) < MS_24H]
        fills_24h.sort(key=lambda x: x.get("time", 0), reverse=True)
    except Exception:
        fills_24h = []

    # 7d funding
    try:
        fund_hist = get_user_funding(address, now_ms - MS_7D)
        funding_7d = {}
        total_funding_7d = 0.0
        for f in fund_hist:
            if "delta" in f and "funding" in f["delta"]:
                coin = f["delta"].get("coin", "UNKNOWN")
                amt = float(f["delta"]["funding"])
                funding_7d[coin] = funding_7d.get(coin, 0) + amt
                total_funding_7d += amt
    except Exception:
        funding_7d = {}
        total_funding_7d = 0.0

    # Fees
    try:
        fees = get_user_fees(address)
    except Exception:
        fees = {}

    # Positions
    positions = []
    total_notional = 0.0
    for p in state.get("assetPositions", []):
        szi = float(p["position"]["szi"])
        if szi == 0:
            continue
        coin = p["position"]["coin"]
        entry_px = float(p["position"]["entryPx"] or 0)
        mark_px = mark_prices.get(coin, entry_px)
        liq_px = float(p["position"]["liquidationPx"] or 0)
        margin = float(p["position"]["marginUsed"])
        upnl = float(p["position"]["unrealizedPnl"])
        leverage = float(p["position"]["leverage"].get("value", 1))
        fr = funding_rates.get(coin, 0)
        notional = abs(szi) * mark_px
        total_notional += notional

        # Current funding cost if held 24h
        daily_funding_cost = szi * mark_px * fr * 3  # 3 payments/day

        # Liquidation distance
        if liq_px > 0 and mark_px > 0:
            liq_dist = abs(mark_px - liq_px) / mark_px * 100
        else:
            liq_dist = None

        positions.append({
            "coin": coin,
            "side": "LONG" if szi > 0 else "SHORT",
            "size": abs(szi),
            "notional_usd": round(notional, 2),
            "entry_px": entry_px,
            "mark_px": mark_px,
            "liq_px": liq_px,
            "liq_dist_pct": round(liq_dist, 2) if liq_dist else None,
            "leverage": leverage,
            "margin_usd": round(margin, 2),
            "upnl_usd": round(upnl, 2),
            "upnl_pct": round(upnl / margin * 100, 2) if margin > 0 else 0,
            "daily_funding_usd": round(daily_funding_cost, 4),
            "funding_8h_pct": round(fr * 100, 4),
        })

    positions.sort(key=lambda x: abs(x["notional_usd"]), reverse=True)

    # Realized PnL from fills
    realized_24h = sum(float(f.get("closedPnl", 0)) for f in fills_24h)
    fees_paid_24h = sum(float(f.get("fee", 0)) for f in fills_24h)

    account_value = float(ms.get("accountValue", 0))
    margin_used = float(ms.get("totalMarginUsed", 0))
    upnl_total = float(ms.get("totalUnrealizedPnl", 0))
    withdrawable = float(state.get("withdrawable", 0))

    return {
        "timestamp": now_ms,
        "generated_at": ts_to_str(now_ms),
        "address": address,
        "account": {
            "value_usd": round(account_value, 2),
            "margin_used_usd": round(margin_used, 2),
            "margin_utilization_pct": round(margin_used / account_value * 100, 2) if account_value > 0 else 0,
            "total_upnl_usd": round(upnl_total, 2),
            "withdrawable_usd": round(withdrawable, 2),
            "total_notional_usd": round(total_notional, 2),
        },
        "pnl": {
            "unrealized_total_usd": round(upnl_total, 2),
            "realized_24h_usd": round(realized_24h, 2),
            "fees_paid_24h_usd": round(fees_paid_24h, 4),
            "funding_7d_usd": round(total_funding_7d, 4),
            "funding_by_coin": {k: round(v, 4) for k, v in sorted(funding_7d.items(), key=lambda x: abs(x[1]), reverse=True)},
        },
        "positions": positions,
        "positions_count": len(positions),
        "spot_balances": spot_balances,
        "recent_fills_24h": fills_24h[:20],
        "fills_count_24h": len(fills_24h),
        "fees": {
            "maker_rate": fees.get("makerFeeRate", "?"),
            "taker_rate": fees.get("takerFeeRate", "?"),
        },
    }


def format_text(r: dict) -> str:
    acc = r["account"]
    pnl = r["pnl"]
    lines = [
        f"# Hyperliquid Portfolio Report",
        f"Generated: {r['generated_at']}",
        f"",
        f"## Account Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Portfolio Value | **${acc['value_usd']:,.2f}** |",
        f"| Unrealized PnL | **{'+' if pnl['unrealized_total_usd'] >= 0 else ''}${pnl['unrealized_total_usd']:,.2f}** |",
        f"| Realized PnL (24h) | ${pnl['realized_24h_usd']:,.2f} |",
        f"| Fees Paid (24h) | ${pnl['fees_paid_24h_usd']:.4f} |",
        f"| 7d Funding Net | {'received' if pnl['funding_7d_usd'] >= 0 else 'paid'} **${abs(pnl['funding_7d_usd']):.4f}** |",
        f"| Margin Used | ${acc['margin_used_usd']:,.2f} ({acc['margin_utilization_pct']:.1f}%) |",
        f"| Total Notional | ${acc['total_notional_usd']:,.2f} |",
        f"| Withdrawable | ${acc['withdrawable_usd']:,.2f} |",
        f"| Fee Tier | maker {r['fees']['maker_rate']} / taker {r['fees']['taker_rate']} |",
        f"",
    ]

    if r["positions"]:
        lines.append(f"## Open Positions ({r['positions_count']})\n")
        lines.append("| Coin | Side | Notional | Entry | Mark | PnL | Lev | Liq Dist | Daily Funding |")
        lines.append("|------|------|----------|-------|------|-----|-----|----------|---------------|")
        for p in r["positions"]:
            pnl_str = f"{p['upnl_pct']:+.1f}% (${p['upnl_usd']:+.2f})"
            liq_str = f"{p['liq_dist_pct']:.1f}%" if p["liq_dist_pct"] else "—"
            fund_str = f"${p['daily_funding_usd']:+.3f}/d"
            lines.append(
                f"| **{p['coin']}** | {p['side']} | ${p['notional_usd']:,.0f} | "
                f"${p['entry_px']:,.4g} | ${p['mark_px']:,.4g} | "
                f"{pnl_str} | {p['leverage']:.0f}x | {liq_str} | {fund_str} |"
            )
        lines.append("")

    if r["fills_count_24h"] > 0:
        lines.append(f"## Recent Trades (24h) — {r['fills_count_24h']} fills\n")
        for f in r["recent_fills_24h"][:10]:
            side = "BUY" if f.get("side") == "B" else "SELL"
            pnl_str = f"  PnL ${float(f.get('closedPnl', 0)):+.4f}" if float(f.get("closedPnl", 0)) != 0 else ""
            lines.append(
                f"- {ts_to_str(int(f.get('time', 0)))} | {f.get('coin', '?')} {side} "
                f"{f.get('sz', '?')} @ ${f.get('px', '?')}{pnl_str}"
            )
        lines.append("")

    if pnl["funding_by_coin"]:
        lines.append("## 7d Funding by Coin\n")
        for coin, amt in list(pnl["funding_by_coin"].items())[:8]:
            direction = "received" if amt >= 0 else "paid"
            lines.append(f"- **{coin}**: {direction} ${abs(amt):.4f}")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid portfolio report")
    parser.add_argument("--address", help="Wallet address (overrides env)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    addr = args.address or wallet_address()
    result = run_report(addr)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))
