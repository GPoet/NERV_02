#!/usr/bin/env python3
from __future__ import annotations
"""
hl_intel.py — Full Hyperliquid intelligence engine.

Orchestrates:
  1. Leaderboard scan — top 20 traders by allTime PnL, positions + win rates
  2. Market scanner — funding extremes, vol spikes, momentum across all 229 perps
  3. Macro layer — BTC regime, fear/greed, dominance, ETH/BTC rotation
  4. Consensus detection — coins where multiple whales agree on direction
  5. Strategy generation — ranked trade ideas with conviction scores

Usage:
    python intel.py [--json] [--quick] [--depth 20]

Flags:
    --quick    : skip win rate computation (faster, fewer API calls)
    --depth N  : analyse top N traders (default 20)
    --json     : raw JSON output (for downstream Claude synthesis)
"""
import sys
import json
import time
import argparse
import math

import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.dirname(_here))

from hl.leaderboard import run_leaderboard_scan
from hl.scanner     import run_scan
from hl.macro       import run_macro_scan


# ── Strategy generation ───────────────────────────────────────────────────────

def score_strategy(
    coin: str,
    direction: str,
    signals: list[str],
    funding_apr: float,
    vol_oi: float,
    change_24h: float,
    macro_bias: str,
    consensus: dict | None,
    fear_greed: int,
) -> dict:
    """
    Generate a trade idea with conviction score.
    Returns dict with all fields needed for a trade brief.
    """
    score = 0
    reasons = []

    # 1. Macro alignment (±15 pts)
    long = direction == "LONG"
    if macro_bias == "RISK_ON"  and long:  score += 15; reasons.append("macro risk-on supports longs")
    if macro_bias == "RISK_OFF" and not long: score += 15; reasons.append("macro risk-off supports shorts")
    if macro_bias == "RISK_ON"  and not long: score -= 5
    if macro_bias == "RISK_OFF" and long:     score -= 5

    # 2. Whale consensus (up to 45 pts)
    if consensus:
        aligned = consensus.get("aligned_count", 0)
        conv    = consensus.get("conviction", "LOW")
        agree   = consensus.get("agreement_pct", 0)
        if conv == "HIGH":   score += 45; reasons.append(f"{aligned} top whales aligned {direction}")
        elif conv == "MEDIUM": score += 25; reasons.append(f"{aligned} whales agree {direction}")
        else:                 score += 10; reasons.append(f"whale position exists")
        # Bonus for very high agreement
        if agree >= 99.9 and aligned >= 5: score += 10; reasons.append("100% unanimous whale consensus")

    # 3. Funding rate edge (up to 25 pts)
    # Extreme negative funding = longs getting paid → short squeeze incoming (LONG setup)
    # Extreme positive funding = shorts getting paid → long squeeze incoming (SHORT setup)
    if long  and funding_apr < -80:  score += 25; reasons.append(f"funding {funding_apr:.0f}% APR — shorts squeezed")
    if long  and funding_apr < -40:  score += 15; reasons.append(f"funding {funding_apr:.0f}% APR — short bias extreme")
    if not long and funding_apr > 80: score += 25; reasons.append(f"funding {funding_apr:.0f}% APR — longs bleeding")
    if not long and funding_apr > 40: score += 15; reasons.append(f"funding {funding_apr:.0f}% APR — crowded longs")

    # 4. Volume confirmation (up to 15 pts)
    if vol_oi > 2.0: score += 15; reasons.append(f"volume {vol_oi:.1f}x OI — major breakout activity")
    elif vol_oi > 1.5: score += 8; reasons.append(f"volume spike {vol_oi:.1f}x OI")

    # 5. Momentum alignment (up to 10 pts)
    if long  and change_24h > 5:   score += 10; reasons.append(f"+{change_24h:.1f}% momentum")
    if long  and change_24h < -8:  score += 5;  reasons.append(f"oversold bounce setup {change_24h:.1f}%")
    if not long and change_24h < -5: score += 10; reasons.append(f"{change_24h:.1f}% breakdown")
    if not long and change_24h > 8: score += 5;  reasons.append(f"overbought fade {change_24h:.1f}%")

    # 6. Sentiment contrarian bonus (5 pts)
    if fear_greed <= 20 and long:    score += 5; reasons.append("extreme fear — contrarian long")
    if fear_greed >= 80 and not long: score += 5; reasons.append("extreme greed — contrarian short")

    # Conviction label
    if score >= 40:   conviction = "HIGH"
    elif score >= 22: conviction = "MEDIUM"
    else:             conviction = "LOW"

    return {
        "coin":       coin,
        "direction":  direction,
        "score":      score,
        "conviction": conviction,
        "reasons":    reasons,
        "signals":    signals,
        "funding_apr": funding_apr,
    }


def generate_strategies(
    market_scan: dict,
    leaderboard: dict,
    macro: dict,
) -> list[dict]:
    """Combine all signals into ranked strategy ideas."""
    strategies = []
    macro_bias  = macro["derived"]["overall_bias"]
    fg_val      = macro["fear_greed"].get("value", 50)
    consensus   = leaderboard.get("consensus_alltime", {})
    alt_season  = macro["derived"].get("alt_season", False)

    # Index market data by coin
    market_by_coin = {r["coin"]: r for r in market_scan.get("top_opportunities", [])}
    # Add extreme funding coins
    for r in market_scan.get("extreme_funding", []):
        market_by_coin.setdefault(r["coin"], r)

    # --- Strategy pool 1: High-conviction consensus trades ---
    for coin, cons in consensus.items():
        if cons["aligned_count"] < 2:
            continue
        direction = cons["direction"]
        mkt = market_by_coin.get(coin, {})
        signals = ["WHALE_CONSENSUS"]
        if mkt.get("vol_oi_ratio", 0) > 1.5: signals.append("VOLUME_SPIKE")
        if abs(mkt.get("funding_apr_pct", 0)) > 40: signals.append("FUNDING_EXTREME")

        s = score_strategy(
            coin=coin, direction=direction, signals=signals,
            funding_apr=mkt.get("funding_apr_pct", 0),
            vol_oi=mkt.get("vol_oi_ratio", 0),
            change_24h=mkt.get("change_24h_pct", 0),
            macro_bias=macro_bias,
            consensus=cons,
            fear_greed=fg_val,
        )
        # mark_px: prefer scanner data, fall back to whale avg entry
        _mark = mkt.get("mark_px")
        mark_px = _mark if _mark is not None else cons.get("avg_entry", 0)
        s.update({
            "whale_agreement": f"{cons['aligned_count']}/{cons['total_traders']} ({cons['agreement_pct']:.0f}%)",
            "whale_avg_entry": cons["avg_entry"],
            "whale_names":     cons["traders"][:4],
            "mark_px":         mark_px,
            "oi_usd_m":        mkt.get("oi_usd_m", 0),
            "source":          "WHALE_CONSENSUS",
        })
        strategies.append(s)

    # --- Strategy pool 2: Funding mean-reversion plays ---
    for r in market_scan.get("extreme_funding", []):
        apr = r["funding_apr_pct"]
        coin = r["coin"]
        # Shorts paying → mean reversion LONG (funding will reset down)
        if apr < -80:
            direction = "LONG"
            signals = ["FUNDING_EXTREME", "MEAN_REVERSION"]
        # Longs paying hugely → fade / SHORT
        elif apr > 80:
            direction = "SHORT"
            signals = ["FUNDING_EXTREME", "MEAN_REVERSION"]
        else:
            continue

        # Don't duplicate if already in consensus
        if any(s["coin"] == coin and s["direction"] == direction for s in strategies):
            cons_data = consensus.get(coin)
            # Reinforce existing entry instead
            for s in strategies:
                if s["coin"] == coin:
                    s["signals"].append("FUNDING_EXTREME")
                    s["score"] += 15
            continue

        s = score_strategy(
            coin=coin, direction=direction, signals=signals,
            funding_apr=apr, vol_oi=r.get("vol_oi_ratio", 0),
            change_24h=r.get("change_24h_pct", 0),
            macro_bias=macro_bias, consensus=None, fear_greed=fg_val,
        )
        s.update({
            "mark_px":   r["mark_px"],
            "oi_usd_m":  r["oi_usd_m"],
            "source":    "FUNDING_MEAN_REVERSION",
            "note":      f"Funding {apr:.0f}% APR unsustainable — expect reversion within 1-3 days",
        })
        strategies.append(s)

    # --- Strategy pool 3: Volume breakouts ---
    for r in market_scan.get("volume_spikes", []):
        coin = r["coin"]
        chg  = r["change_24h_pct"]
        direction = "LONG" if chg > 0 else "SHORT"
        if any(s["coin"] == coin for s in strategies):
            continue

        signals = ["VOLUME_SPIKE", "MOMENTUM"]
        s = score_strategy(
            coin=coin, direction=direction, signals=signals,
            funding_apr=r.get("funding_apr_pct", 0), vol_oi=r["vol_oi_ratio"],
            change_24h=chg, macro_bias=macro_bias, consensus=None, fear_greed=fg_val,
        )
        s.update({
            "mark_px":  r["mark_px"],
            "oi_usd_m": r["oi_usd_m"],
            "source":   "VOLUME_BREAKOUT",
            "note":     f"Unusual volume {r['vol_oi_ratio']:.1f}x OI with {chg:+.1f}% move",
        })
        strategies.append(s)

    # --- Strategy pool 4: BTC macro play ---
    btc_mkt = market_by_coin.get("BTC", {})
    if btc_mkt:
        btc_cons = consensus.get("BTC")
        direction = "LONG" if macro_bias == "RISK_ON" else "SHORT"
        signals = ["MACRO_ALIGNMENT"]
        if btc_cons:
            signals.append("WHALE_CONSENSUS")

        if not any(s["coin"] == "BTC" for s in strategies):
            s = score_strategy(
                coin="BTC", direction=direction, signals=signals,
                funding_apr=btc_mkt.get("funding_apr_pct", 0),
                vol_oi=btc_mkt.get("vol_oi_ratio", 0),
                change_24h=btc_mkt.get("change_24h_pct", 0),
                macro_bias=macro_bias, consensus=btc_cons, fear_greed=fg_val,
            )
            btc_data = macro.get("btc_metrics", {})
            s.update({
                "mark_px":  btc_data.get("btc_price", btc_mkt.get("mark_px", 0)),
                "oi_usd_m": btc_mkt.get("oi_usd_m", 0),
                "source":   "MACRO_PLAY",
                "note":     f"Macro regime: {macro['btc_metrics'].get('market_regime')} | BTC 30d: {btc_data.get('btc_30d_pct',0):+.1f}%",
            })
            strategies.append(s)

    # Sort by score
    strategies.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate same coin/direction
    seen = set()
    deduped = []
    for s in strategies:
        key = (s["coin"], s["direction"])
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return deduped[:12]  # top 12 ideas


# ── Risk framework ────────────────────────────────────────────────────────────

def compute_risk_params(mark_px: float, direction: str, oi_usd_m: float, conviction: str) -> dict:
    """Estimate entry zone, stop, and target based on conviction and volatility proxy."""
    # Volatility proxy: smaller OI = more volatile
    if oi_usd_m < 10:
        vol_factor = 0.05   # 5% moves
    elif oi_usd_m < 100:
        vol_factor = 0.03   # 3% moves
    elif oi_usd_m < 1000:
        vol_factor = 0.02   # 2% moves
    else:
        vol_factor = 0.015  # BTC-level

    # Conviction affects R:R target
    r_mult = {"HIGH": 3.0, "MEDIUM": 2.0, "LOW": 1.5}.get(conviction, 2.0)
    stop_pct = vol_factor * 1.5   # 1.5x vol
    target_pct = stop_pct * r_mult

    if direction == "LONG":
        entry_low  = round(mark_px * (1 - vol_factor * 0.3), 4)
        entry_high = round(mark_px * (1 + vol_factor * 0.2), 4)
        stop       = round(mark_px * (1 - stop_pct), 4)
        target1    = round(mark_px * (1 + target_pct * 0.6), 4)
        target2    = round(mark_px * (1 + target_pct), 4)
    else:
        entry_low  = round(mark_px * (1 - vol_factor * 0.2), 4)
        entry_high = round(mark_px * (1 + vol_factor * 0.3), 4)
        stop       = round(mark_px * (1 + stop_pct), 4)
        target1    = round(mark_px * (1 - target_pct * 0.6), 4)
        target2    = round(mark_px * (1 - target_pct), 4)

    return {
        "entry_zone":    [entry_low, entry_high],
        "stop":          stop,
        "target1":       target1,
        "target2":       target2,
        "stop_pct":      round(stop_pct * 100, 2),
        "target1_pct":   round(target_pct * 0.6 * 100, 2),
        "target2_pct":   round(target_pct * 100, 2),
        "risk_reward":   round(r_mult, 1),
    }


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_intel(depth: int = 20, quick: bool = False) -> dict:
    """Full intel scan. depth = number of traders to analyse."""
    print(f"[intel] Starting scan: depth={depth}, quick={quick}", file=sys.stderr)

    t0 = time.time()

    # 1. Market structure (fast)
    print("[intel] Scanning market structure...", file=sys.stderr)
    market = run_scan(top_n=20)

    # 2. Macro (medium)
    print("[intel] Fetching macro data...", file=sys.stderr)
    macro = run_macro_scan()

    # 3. Leaderboard (slowest — parallel fetch)
    print(f"[intel] Fetching leaderboard (top {depth} traders)...", file=sys.stderr)
    lb = run_leaderboard_scan(top_n=depth, deep_n=0 if quick else min(depth, 10))

    # 4. Strategy generation
    print("[intel] Generating strategies...", file=sys.stderr)
    strategies = generate_strategies(market, lb, macro)

    # 5. Enrich strategies with risk params
    for s in strategies:
        if s.get("mark_px", 0) > 0:
            s["risk_params"] = compute_risk_params(
                s["mark_px"], s["direction"], s.get("oi_usd_m", 1), s["conviction"]
            )

    elapsed = round(time.time() - t0, 1)
    print(f"[intel] Done in {elapsed}s", file=sys.stderr)

    return {
        "generated_at":   time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "elapsed_sec":    elapsed,
        "market_scan":    market,
        "macro":          macro,
        "leaderboard":    lb,
        "strategies":     strategies,
        "top_strategies": strategies[:5],
        "summary": {
            "market_regime":   macro["btc_metrics"].get("market_regime", "?"),
            "macro_bias":      macro["derived"]["overall_bias"],
            "fear_greed":      macro["fear_greed"].get("value", 50),
            "fear_greed_cls":  macro["fear_greed"].get("classification", "?"),
            "btc_price":       macro["btc_metrics"].get("btc_price", 0),
            "btc_dominance":   macro["global"].get("btc_dominance_pct", 0),
            "alt_season":      macro["derived"].get("alt_season", False),
            "top_strategies":  [f"{s['coin']} {s['direction']} ({s['conviction']})" for s in strategies[:5]],
            "high_conviction_count": len([s for s in strategies if s["conviction"] == "HIGH"]),
            "total_markets_scanned": market.get("total_markets", 0),
            "traders_analysed": len(lb.get("top_traders", [])),
        },
    }


def format_brief(intel: dict) -> str:
    """Human-readable intel brief."""
    s = intel["summary"]
    macro = intel["macro"]
    lb = intel["leaderboard"]
    strategies = intel["strategies"]

    fg = macro["fear_greed"]
    btc = macro["btc_metrics"]
    g = macro["global"]
    derived = macro["derived"]

    lines = [
        f"# HYPERLIQUID INTEL BRIEF",
        f"Generated: {intel['generated_at']}",
        f"",
        f"## MACRO OVERVIEW",
        f"| Signal | Value |",
        f"|--------|-------|",
        f"| Market Regime | **{s['market_regime']}** |",
        f"| Macro Bias | **{s['macro_bias']}** |",
        f"| Fear/Greed | **{s['fear_greed']} — {s['fear_greed_cls']}** (yesterday: {fg.get('yesterday')}, trend: {fg.get('trend')}) |",
        f"| BTC Price | **${s['btc_price']:,.0f}** |",
        f"| BTC 24h | {btc.get('btc_24h_pct',0):+.2f}% | 7d: {btc.get('btc_7d_pct',0):+.2f}% | 30d: {btc.get('btc_30d_pct',0):+.2f}% |",
        f"| BTC Dominance | {s['btc_dominance']}% -> {derived['dom_signal'][:40]} |",
        f"| ETH/BTC Ratio | {btc.get('eth_btc_ratio', 0):.5f} |",
        f"| Total Market Cap | ${g.get('total_market_cap_usd', 0)/1e12:.2f}T ({g.get('market_cap_change_24h', 0):+.1f}% 24h) |",
        f"| Alt Season | {'YES' if s['alt_season'] else 'NO'} |",
        f"",
        f"**Macro note**: {derived['bias_note']}",
        f"",
    ]

    # Whale consensus
    consensus = lb.get("consensus_alltime", {})
    high_conv = {k: v for k, v in consensus.items() if v["conviction"] in ("HIGH", "MEDIUM")}
    if high_conv:
        lines += [f"## WHALE CONSENSUS (Top-PnL Traders)", ""]
        for coin, c in list(high_conv.items())[:8]:
            lines.append(
                f"- **{coin} {c['direction']}** | {c['aligned_count']}/{c['total_traders']} whales "
                f"({c['agreement_pct']:.0f}% agreement) | Notional: ${c['total_notional']:,.0f} | "
                f"Avg entry: ${c['avg_entry']:,.4g} | **{c['conviction']}**"
            )
            if c.get("traders"):
                lines.append(f"  Traders: {', '.join(c['traders'][:4])}")
        lines.append("")

    # Top traders summary
    top_traders = lb.get("top_traders", [])[:8]
    if top_traders:
        lines += [f"## TOP TRADERS (by all-time PnL)", ""]
        lines.append("| Name | All-time PnL | 30d PnL | Win Rate | Positions |")
        lines.append("|------|-------------|---------|----------|-----------|")
        for t in top_traders:
            wr = t.get("trade_stats", {}).get("win_rate")
            wr_str = f"{wr:.1f}%" if wr is not None else "—"
            lines.append(
                f"| {t['display'][:18]} | ${t['all_time']['pnl']:,.0f} | "
                f"${t['month']['pnl']:,.0f} | {wr_str} | {len(t.get('positions', []))} |"
            )
        lines.append("")

    # Market structure
    mkt = intel["market_scan"]
    lines += ["## MARKET STRUCTURE", ""]
    if mkt.get("extreme_funding"):
        lines.append("**Extreme Funding Rates:**")
        for r in mkt["extreme_funding"][:6]:
            d = "LONGS PAYING" if r["funding_apr_pct"] > 0 else "SHORTS PAYING"
            lines.append(
                f"  - {r['coin']}: {r['funding_apr_pct']:+.0f}% APR | {d} | OI ${r['oi_usd_m']:.1f}M"
            )
        lines.append("")
    if mkt.get("volume_spikes"):
        lines.append("**Volume Spikes:**")
        for r in mkt["volume_spikes"]:
            lines.append(f"  - {r['coin']}: {r['vol_oi_ratio']:.1f}x OI | ${r['volume_24h_m']:.1f}M vol | {r['change_24h_pct']:+.1f}%")
        lines.append("")
    movers_str = ', '.join(f"{r['coin']} {r['change_24h_pct']:+.1f}%" for r in mkt.get('top_movers_24h', [])[:5])
    lines.append(f"**Top movers 24h:** {movers_str}")
    lines.append("")

    # Trending on CoinGecko
    trending = macro.get("trending", [])
    if trending:
        lines.append(f"**Trending (social):** {', '.join(c['symbol'] for c in trending)}")
        lines.append("")

    # Strategies
    lines += [f"## TRADE STRATEGIES ({len(strategies)} ideas, {s['high_conviction_count']} HIGH conviction)", ""]
    for i, strat in enumerate(strategies[:8], 1):
        rp = strat.get("risk_params", {})
        conv_emoji = "🔴" if strat["conviction"] == "HIGH" else "🟡" if strat["conviction"] == "MEDIUM" else "⚪"
        lines.append(
            f"### #{i} {strat['coin']} {strat['direction']} {conv_emoji} {strat['conviction']} "
            f"(score {strat['score']})"
        )
        lines.append(f"**Source**: {strat['source']}")
        if strat.get("reasons"):
            lines.append(f"**Why**: {' | '.join(strat['reasons'][:4])}")
        if strat.get("note"):
            lines.append(f"**Note**: {strat['note']}")
        if rp:
            lines.append(
                f"**Entry**: ${rp['entry_zone'][0]:,.4g} – ${rp['entry_zone'][1]:,.4g} | "
                f"**Stop**: ${rp['stop']:,.4g} (-{rp['stop_pct']:.1f}%) | "
                f"**T1**: ${rp['target1']:,.4g} (+{rp['target1_pct']:.1f}%) | "
                f"**T2**: ${rp['target2']:,.4g} (+{rp['target2_pct']:.1f}%) | "
                f"R:R {rp['risk_reward']:.1f}x"
            )
        if strat.get("whale_agreement"):
            lines.append(f"**Whale agreement**: {strat['whale_agreement']} — {', '.join(strat.get('whale_names', [])[:3])}")
        # HL trade command
        if rp:
            sz_note = "size TBD"
            if strat["direction"] == "LONG":
                cmd = f"BUY {strat['coin']} {{SIZE}} limit {rp['entry_zone'][0]} sl {rp['stop']} tp {rp['target1']}"
            else:
                cmd = f"SELL {strat['coin']} {{SIZE}} limit {rp['entry_zone'][1]} sl {rp['stop']} tp {rp['target1']}"
            lines.append(f"**Execute**: `hl-trade: {cmd}`")
        lines.append("")

    lines += [
        f"---",
        f"*{s['total_markets_scanned']} markets scanned | {s['traders_analysed']} traders analysed | {intel['elapsed_sec']}s*"
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid Intel Engine")
    parser.add_argument("--depth", type=int, default=20, help="Traders to analyse")
    parser.add_argument("--quick", action="store_true", help="Skip win rate (faster)")
    parser.add_argument("--json", action="store_true", help="Raw JSON output")
    args = parser.parse_args()

    result = run_intel(depth=args.depth, quick=args.quick)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_brief(result))
