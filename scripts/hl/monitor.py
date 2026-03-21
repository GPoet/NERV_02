#!/usr/bin/env python3
"""
hl_monitor.py — Hyperliquid position monitor.

Reads open positions, calculates liquidation distances,
unrealized PnL, funding costs, and margin health.

Usage:
    HL_WALLET_ADDRESS=0x... python monitor.py [--json]

Env vars:
    HL_WALLET_ADDRESS  — wallet to monitor (required)
    HL_PRIVATE_KEY     — needed only if HL_WALLET_ADDRESS not set
"""
import sys
import json
import time
import argparse

import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.dirname(_here))
from hl.client import (
    get_clearinghouse_state, get_spot_state,
    get_open_orders, get_user_fees, get_user_funding,
    get_meta_and_asset_ctxs, wallet_address,
)

MS_7D = 7 * 24 * 3600 * 1000


def analyse_position(pos: dict, mark_prices: dict) -> dict:
    """Enrich a raw position with computed risk metrics."""
    coin = pos["position"]["coin"]
    size = float(pos["position"]["szi"])
    entry_px = float(pos["position"]["entryPx"] or 0)
    liq_px = float(pos["position"]["liquidationPx"] or 0)
    leverage = float(pos["position"]["leverage"].get("value", 1))
    margin_used = float(pos["position"]["marginUsed"])
    unrealized_pnl = float(pos["position"]["unrealizedPnl"])
    cum_funding = float(pos["position"]["cumFunding"].get("sinceChange", 0))
    is_long = size > 0

    mark_px = float(mark_prices.get(coin, entry_px))

    # Liquidation distance
    if liq_px > 0 and mark_px > 0:
        if is_long:
            liq_distance_pct = (mark_px - liq_px) / mark_px * 100
        else:
            liq_distance_pct = (liq_px - mark_px) / mark_px * 100
    else:
        liq_distance_pct = None

    # PnL %
    if entry_px > 0 and margin_used > 0:
        pnl_pct = unrealized_pnl / margin_used * 100
    else:
        pnl_pct = 0.0

    # Risk flags
    flags = []
    if liq_distance_pct is not None and liq_distance_pct < 10:
        flags.append(f"LIQUIDATION_RISK ({liq_distance_pct:.1f}% from liq)")
    if abs(unrealized_pnl) / max(margin_used, 1) > 0.5:
        flags.append("LARGE_DRAWDOWN" if unrealized_pnl < 0 else "LARGE_GAIN")
    if leverage > 15:
        flags.append(f"HIGH_LEVERAGE ({leverage:.0f}x)")

    return {
        "coin": coin,
        "side": "LONG" if is_long else "SHORT",
        "size": abs(size),
        "entry_px": entry_px,
        "mark_px": mark_px,
        "liq_px": liq_px,
        "leverage": leverage,
        "margin_used_usd": round(margin_used, 2),
        "unrealized_pnl_usd": round(unrealized_pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "liq_distance_pct": round(liq_distance_pct, 2) if liq_distance_pct is not None else None,
        "cum_funding_usd": round(cum_funding, 4),
        "flags": flags,
    }


def run_monitor(address: str) -> dict:
    state = get_clearinghouse_state(address)

    # Current mark prices from meta
    try:
        meta_ctxs = get_meta_and_asset_ctxs()
        universe = meta_ctxs[0]["universe"]
        ctxs = meta_ctxs[1]
        mark_prices = {
            universe[i]["name"]: ctxs[i].get("markPx", "0")
            for i in range(min(len(universe), len(ctxs)))
            if ctxs[i]
        }
    except Exception:
        mark_prices = {}

    # Account summary
    margin_summary = state.get("marginSummary", {})
    account_value = float(margin_summary.get("accountValue", 0))
    total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
    total_raw_usd = float(margin_summary.get("totalRawUsd", 0))
    total_pnl = float(margin_summary.get("totalUnrealizedPnl", 0))
    withdrawable = float(state.get("withdrawable", 0))

    # Positions
    raw_positions = [
        p for p in state.get("assetPositions", [])
        if float(p["position"]["szi"]) != 0
    ]
    positions = [analyse_position(p, mark_prices) for p in raw_positions]

    # Open orders
    try:
        open_orders = get_open_orders(address)
    except Exception:
        open_orders = []

    # 7d funding history
    try:
        funding_hist = get_user_funding(address, int(time.time() * 1000) - MS_7D)
        total_funding_7d = sum(float(f["delta"].get("funding", 0)) for f in funding_hist if "delta" in f)
    except Exception:
        total_funding_7d = 0.0

    # Fees tier
    try:
        fees = get_user_fees(address)
        maker_rate = fees.get("makerFeeRate", "?")
        taker_rate = fees.get("takerFeeRate", "?")
    except Exception:
        maker_rate = taker_rate = "?"

    # Risk assessment
    if account_value > 0:
        margin_utilization = total_margin_used / account_value * 100
    else:
        margin_utilization = 0.0

    overall_risk = "OK"
    if margin_utilization > 80:
        overall_risk = "CRITICAL"
    elif margin_utilization > 60:
        overall_risk = "HIGH"
    elif margin_utilization > 40:
        overall_risk = "MODERATE"

    # Any positions with flags
    flagged = [p for p in positions if p["flags"]]

    return {
        "timestamp": int(time.time()),
        "address": address,
        "account": {
            "value_usd": round(account_value, 2),
            "total_margin_used_usd": round(total_margin_used, 2),
            "margin_utilization_pct": round(margin_utilization, 2),
            "total_unrealized_pnl_usd": round(total_pnl, 2),
            "withdrawable_usd": round(withdrawable, 2),
            "funding_7d_usd": round(total_funding_7d, 4),
            "maker_fee": maker_rate,
            "taker_fee": taker_rate,
        },
        "overall_risk": overall_risk,
        "positions": positions,
        "open_orders_count": len(open_orders),
        "open_orders": open_orders[:20],
        "flagged_positions": flagged,
    }


def format_text(m: dict) -> str:
    acc = m["account"]
    lines = [
        f"## Hyperliquid Position Monitor",
        f"Address: `{m['address'][:8]}...{m['address'][-6:]}`",
        f"Risk Status: **{m['overall_risk']}**",
        f"",
        f"### Account Summary",
        f"- Portfolio Value: **${acc['value_usd']:,.2f}**",
        f"- Unrealized PnL: **{'+' if acc['total_unrealized_pnl_usd'] >= 0 else ''}${acc['total_unrealized_pnl_usd']:,.2f}**",
        f"- Margin Used: ${acc['total_margin_used_usd']:,.2f} ({acc['margin_utilization_pct']:.1f}% utilization)",
        f"- Withdrawable: ${acc['withdrawable_usd']:,.2f}",
        f"- 7d Funding: {'received' if acc['funding_7d_usd'] >= 0 else 'paid'} ${abs(acc['funding_7d_usd']):,.4f}",
        f"- Fees: maker {acc['maker_fee']} / taker {acc['taker_fee']}",
        f"",
    ]

    if m["positions"]:
        lines.append(f"### Open Positions ({len(m['positions'])})\n")
        for p in m["positions"]:
            flag_str = f" ⚠️ {', '.join(p['flags'])}" if p["flags"] else ""
            liq_str = f"Liq ${p['liq_px']:,.4g} ({p['liq_distance_pct']:.1f}% away)" if p["liq_distance_pct"] is not None else "Liq N/A"
            lines.append(
                f"**{p['coin']} {p['side']}** | Size {p['size']:.4g} | "
                f"Entry ${p['entry_px']:,.4g} → Mark ${p['mark_px']:,.4g} | "
                f"PnL **{p['pnl_pct']:+.1f}%** (${p['unrealized_pnl_usd']:+.2f}) | "
                f"{liq_str} | {p['leverage']:.0f}x{flag_str}"
            )
    else:
        lines.append("### No Open Positions\n")

    if m["open_orders_count"] > 0:
        lines.append(f"\n### Open Orders: {m['open_orders_count']}")
        for o in m["open_orders"][:5]:
            side = "BUY" if o.get("side") == "B" else "SELL"
            lines.append(f"- {o.get('coin', '?')} {side} {o.get('sz', '?')} @ ${o.get('limitPx', '?')}")

    if m["flagged_positions"]:
        lines.append(f"\n### ⚠️ Flagged Positions")
        for p in m["flagged_positions"]:
            lines.append(f"- **{p['coin']}**: {', '.join(p['flags'])}")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid position monitor")
    parser.add_argument("--address", help="Wallet address (overrides env)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    addr = args.address or wallet_address()
    result = run_monitor(addr)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))
