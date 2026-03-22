#!/usr/bin/env python3
from __future__ import annotations
"""
hl_scanner.py — Hyperliquid market scanner.

Scans all perpetuals for high-conviction setups based on:
  - Extreme funding rates (longs/shorts getting squeezed)
  - Open interest anomalies
  - Volume spikes vs 24h average
  - Price momentum

Usage:
    python scanner.py [--top N] [--json]

Output: ranked list of coins with signal scores + raw metrics.
"""
import sys
import json
import math
import argparse
import time
from typing import Any

import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.dirname(_here))  # scripts/
from hl.client import get_meta_and_asset_ctxs, get_predicted_fundings


def funding_apr(rate_8h: str) -> float:
    """Convert 8h funding rate string to annualised %."""
    try:
        r = float(rate_8h)
        return r * 3 * 365 * 100  # 3 payments/day × 365 days
    except (ValueError, TypeError):
        return 0.0


def score_asset(coin: str, ctx: dict, prev_ctx: dict | None = None) -> dict:
    """
    Score an asset 0-100 for trade opportunity.
    Higher = more interesting (either direction).
    """
    scores = {}

    # 1. Funding rate signal (extremes are mean-reverting)
    apr = funding_apr(ctx.get("funding", "0"))
    fund_score = min(abs(apr) / 2.0, 40)  # cap at 40 pts for 80% APR extreme
    scores["funding"] = fund_score

    # 2. Volume relative to prev day open interest proxy
    ntl_vol = float(ctx.get("dayNtlVlm", 0) or 0)
    oi = float(ctx.get("openInterest", 1) or 1)
    oi_px = float(ctx.get("markPx", 1) or 1)
    oi_usd = oi * oi_px
    vol_oi_ratio = ntl_vol / max(oi_usd, 1)
    vol_score = min(vol_oi_ratio * 10, 20)  # cap at 20 pts
    scores["volume"] = vol_score

    # 3. Price momentum: distance from prev day close
    mark_px = float(ctx.get("markPx", 0) or 0)
    prev_px = float(ctx.get("prevDayPx", mark_px) or mark_px)
    if prev_px > 0:
        change_pct = (mark_px - prev_px) / prev_px * 100
    else:
        change_pct = 0.0
    momentum_score = min(abs(change_pct), 20)  # cap at 20 pts
    scores["momentum"] = momentum_score

    # 4. OI significance (larger markets = more reliable signals)
    oi_score = min(math.log10(max(oi_usd, 1)) - 4, 10)  # 10pts for OI > $100M
    scores["oi_size"] = max(oi_score, 0)

    # 5. Premium / basis spread
    oracle_px = float(ctx.get("oraclePx", mark_px) or mark_px)
    if oracle_px > 0:
        premium_pct = abs(mark_px - oracle_px) / oracle_px * 100
        premium_score = min(premium_pct * 20, 10)  # cap at 10 pts
    else:
        premium_score = 0.0
    scores["premium"] = premium_score

    total = sum(scores.values())

    # Determine signal direction
    if apr > 50:
        signal = "SHORT_BIAS"  # longs paying huge → likely to flip
        reason = f"Funding APR +{apr:.1f}% (longs bleeding)"
    elif apr < -50:
        signal = "LONG_BIAS"   # shorts paying huge → squeeze risk
        reason = f"Funding APR {apr:.1f}% (shorts squeezed)"
    elif abs(change_pct) > 10:
        signal = "MOMENTUM" if change_pct > 0 else "REVERSAL_WATCH"
        reason = f"{change_pct:+.1f}% move today, vol/OI={vol_oi_ratio:.2f}x"
    elif vol_oi_ratio > 1.5:
        signal = "VOLUME_SPIKE"
        reason = f"Volume = {vol_oi_ratio:.1f}x OI (unusual activity)"
    else:
        signal = "NEUTRAL"
        reason = "No strong signal"

    return {
        "coin": coin,
        "score": round(total, 1),
        "signal": signal,
        "reason": reason,
        "mark_px": mark_px,
        "change_24h_pct": round(change_pct, 2),
        "funding_apr_pct": round(apr, 2),
        "funding_8h_pct": round(float(ctx.get("funding", "0")) * 100, 4),
        "oi_usd_m": round(oi_usd / 1e6, 2),
        "volume_24h_m": round(ntl_vol / 1e6, 2),
        "vol_oi_ratio": round(vol_oi_ratio, 2),
        "premium_pct": round(premium_pct if oracle_px > 0 else 0, 4),
    }


def run_scan(top_n: int = 15) -> dict:
    meta_and_ctxs = get_meta_and_asset_ctxs()
    universe = meta_and_ctxs[0]["universe"]
    ctxs = meta_and_ctxs[1]

    results = []
    for i, coin_meta in enumerate(universe):
        if i >= len(ctxs):
            break
        coin = coin_meta["name"]
        ctx = ctxs[i]
        if not ctx:
            continue
        try:
            scored = score_asset(coin, ctx)
            results.append(scored)
        except Exception as e:
            continue

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Get predicted fundings for top coins
    try:
        predicted = get_predicted_fundings()
        pred_map = {}
        for item in predicted:
            if isinstance(item, list) and len(item) == 2:
                coin_name, venues = item
                for venue in venues:
                    if isinstance(venue, list) and len(venue) == 2:
                        venue_name, rate = venue
                        if venue_name == "HyperLiquid":
                            pred_map[coin_name] = round(float(rate) * 100, 4)
    except Exception:
        pred_map = {}

    for r in results:
        r["predicted_funding_8h_pct"] = pred_map.get(r["coin"], None)

    # Categorise
    extreme_funding = [r for r in results if abs(r["funding_apr_pct"]) > 50]
    volume_spikes = [r for r in results if r["vol_oi_ratio"] > 1.5 and r["signal"] != "NEUTRAL"]
    top_movers = sorted(results, key=lambda x: abs(x["change_24h_pct"]), reverse=True)[:5]

    return {
        "timestamp": int(time.time()),
        "total_markets": len(results),
        "top_opportunities": results[:top_n],
        "extreme_funding": extreme_funding[:8],
        "volume_spikes": volume_spikes[:5],
        "top_movers_24h": top_movers,
    }


def format_text(scan: dict) -> str:
    total = scan["total_markets"]
    lines = [
        f"## Hyperliquid Market Scan — {total} markets",
        f"",
    ]

    lines += ["### Top Opportunities", ""]
    for r in scan["top_opportunities"][:10]:
        lines.append(
            f"**{r['coin']}** (score {r['score']}) | ${r['mark_px']:,.4g} | "
            f"{r['change_24h_pct']:+.1f}% | Funding {r['funding_8h_pct']:+.4f}% 8h ({r['funding_apr_pct']:+.1f}% APR) | "
            f"OI ${r['oi_usd_m']:.1f}M | Vol ${r['volume_24h_m']:.1f}M"
        )
        lines.append(f"  -> Signal: **{r['signal']}** — {r['reason']}")
        lines.append("")

    if scan["extreme_funding"]:
        lines += ["### Extreme Funding Rates", ""]
        for r in scan["extreme_funding"]:
            direction = "LONGS PAYING" if r["funding_apr_pct"] > 0 else "SHORTS PAYING"
            lines.append(
                f"**{r['coin']}**: {r['funding_apr_pct']:+.1f}% APR | {direction} | "
                f"OI ${r['oi_usd_m']:.1f}M"
            )
        lines.append("")

    if scan["volume_spikes"]:
        lines += ["### Volume Spikes", ""]
        for r in scan["volume_spikes"]:
            lines.append(f"**{r['coin']}**: {r['vol_oi_ratio']:.1f}x OI | ${r['volume_24h_m']:.1f}M vol | {r['change_24h_pct']:+.1f}%")
        lines.append("")

    lines += ["### Biggest 24h Movers", ""]
    for r in scan["top_movers_24h"]:
        lines.append(f"**{r['coin']}**: {r['change_24h_pct']:+.2f}% | ${r['mark_px']:,.4g}")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid market scanner")
    parser.add_argument("--top", type=int, default=15, help="Number of top results")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    scan = run_scan(top_n=args.top)

    if args.json:
        print(json.dumps(scan, indent=2))
    else:
        print(format_text(scan))
