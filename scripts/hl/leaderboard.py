#!/usr/bin/env python3
"""
Hyperliquid leaderboard + whale intelligence.

Fetches all 30k+ traders, ranks them, then deep-dives
the top N by allTime PnL to extract:
  - Win rate (profitable close trades / all close trades)
  - Preferred coins and directions
  - Current open positions
  - Sizing and leverage patterns
  - Consensus signal (multiple whales aligned = high conviction)
"""
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
HL_INFO = "https://api.hyperliquid.xyz/info"

MS_7D  = 7  * 24 * 3600 * 1000
MS_30D = 30 * 24 * 3600 * 1000


def _hl_post(payload: dict, timeout: int = 12) -> Any:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        HL_INFO, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get_window(row: dict, window: str) -> dict:
    for w in row.get("windowPerformances", []):
        if w[0] == window:
            return w[1]
    return {}


def fetch_leaderboard() -> list[dict]:
    """Fetch full leaderboard (~32k rows). Returns raw list."""
    req = urllib.request.Request(
        LEADERBOARD_URL, headers={"User-Agent": "Mozilla/5.0"}, method="GET"
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read()).get("leaderboardRows", [])


def rank_traders(rows: list[dict], window: str = "allTime", top_n: int = 50) -> list[dict]:
    """Rank traders by PnL for a given window, return enriched top_n."""
    def pnl(r): return float(_get_window(r, window).get("pnl", 0))
    def roi(r): return float(_get_window(r, window).get("roi", 0))
    def vlm(r): return float(_get_window(r, window).get("vlm", 0))

    ranked = sorted(rows, key=pnl, reverse=True)[:top_n]
    result = []
    for r in ranked:
        w_all  = _get_window(r, "allTime")
        w_mo   = _get_window(r, "month")
        w_wk   = _get_window(r, "week")
        w_day  = _get_window(r, "day")
        result.append({
            "address":     r["ethAddress"],
            "display":     r.get("displayName") or r["ethAddress"][:12],
            "account_usd": float(r.get("accountValue", 0)),
            "all_time": {
                "pnl": float(w_all.get("pnl", 0)),
                "roi": float(w_all.get("roi", 0)),
                "vlm": float(w_all.get("vlm", 0)),
            },
            "month": {
                "pnl": float(w_mo.get("pnl", 0)),
                "roi": float(w_mo.get("roi", 0)),
            },
            "week": {
                "pnl": float(w_wk.get("pnl", 0)),
                "roi": float(w_wk.get("roi", 0)),
            },
            "day": {
                "pnl": float(w_day.get("pnl", 0)),
                "roi": float(w_day.get("roi", 0)),
            },
        })
    return result


def compute_win_rate(fills: list[dict]) -> dict:
    """
    From raw fills, compute win rate and trade statistics.
    Only closing trades have meaningful closedPnl.
    """
    closes = [f for f in fills if "Close" in f.get("dir", "")]
    if not closes:
        return {"win_rate": None, "trades": 0, "avg_win": 0, "avg_loss": 0, "ev": 0, "best_coins": []}

    wins  = [f for f in closes if float(f.get("closedPnl", 0)) > 0]
    losses = [f for f in closes if float(f.get("closedPnl", 0)) < 0]

    win_rate = len(wins) / len(closes) if closes else 0
    avg_win  = sum(float(f["closedPnl"]) for f in wins)  / len(wins)  if wins   else 0
    avg_loss = sum(float(f["closedPnl"]) for f in losses) / len(losses) if losses else 0
    ev = win_rate * avg_win + (1 - win_rate) * avg_loss  # Expected value per trade

    # Coin breakdown — what does this trader like trading?
    coin_stats: dict[str, dict] = {}
    for f in closes:
        coin = f["coin"]
        pnl  = float(f.get("closedPnl", 0))
        if coin not in coin_stats:
            coin_stats[coin] = {"total_pnl": 0, "count": 0, "wins": 0}
        coin_stats[coin]["total_pnl"] += pnl
        coin_stats[coin]["count"] += 1
        if pnl > 0:
            coin_stats[coin]["wins"] += 1

    best_coins = sorted(
        [{"coin": c, **v, "win_rate": v["wins"] / v["count"]} for c, v in coin_stats.items()],
        key=lambda x: x["total_pnl"],
        reverse=True,
    )[:8]

    # Hold time analysis (time between open and corresponding close)
    # Approximate via gap between consecutive fills on same coin
    recent = sorted(closes, key=lambda x: x.get("time", 0), reverse=True)
    last_fill_ts = recent[0].get("time", 0) if recent else 0

    return {
        "win_rate":        round(win_rate * 100, 1),
        "trades":          len(closes),
        "wins":            len(wins),
        "losses":          len(losses),
        "avg_win_usd":     round(avg_win, 2),
        "avg_loss_usd":    round(avg_loss, 2),
        "ev_per_trade":    round(ev, 2),
        "total_pnl_fills": round(sum(float(f.get("closedPnl", 0)) for f in closes), 2),
        "best_coins":      best_coins,
        "last_trade_ms":   last_fill_ts,
    }


def fetch_positions(address: str) -> list[dict]:
    """Return non-zero positions with enriched fields."""
    try:
        state = _hl_post({"type": "clearinghouseState", "user": address.lower()})
        ms = state.get("marginSummary", {})
        account_val = float(ms.get("accountValue", 0))
        positions = []
        for p in state.get("assetPositions", []):
            szi = float(p["position"]["szi"])
            if szi == 0:
                continue
            pos = p["position"]
            coin = pos["coin"]
            entry = float(pos.get("entryPx") or 0)
            upnl  = float(pos.get("unrealizedPnl") or 0)
            margin = float(pos.get("marginUsed") or 0)
            lev   = pos.get("leverage", {}).get("value", 0)
            lev_type = pos.get("leverage", {}).get("type", "cross")
            notional = abs(szi) * entry
            positions.append({
                "coin":     coin,
                "side":     "LONG" if szi > 0 else "SHORT",
                "size":     abs(szi),
                "notional": round(notional, 2),
                "entry_px": entry,
                "upnl":     round(upnl, 2),
                "margin":   round(margin, 2),
                "leverage": lev,
                "lev_type": lev_type,
                "pct_of_account": round(notional / account_val * 100, 1) if account_val else 0,
            })
        positions.sort(key=lambda x: x["notional"], reverse=True)
        return positions
    except Exception:
        return []


def fetch_fills_recent(address: str) -> list[dict]:
    """Fetch all available fills (max 2000 by API limit)."""
    try:
        return _hl_post({"type": "userFills", "user": address.lower()})
    except Exception:
        return []


def analyse_trader(trader: dict, deep: bool = True) -> dict:
    """Full analysis of a single trader — positions + win rate."""
    addr = trader["address"]

    positions = fetch_positions(addr)

    stats = {}
    if deep:
        fills = fetch_fills_recent(addr)
        stats = compute_win_rate(fills)

    return {**trader, "positions": positions, "trade_stats": stats}


def build_consensus(traders_analysed: list[dict]) -> dict:
    """
    Find coins where multiple top traders agree on direction.
    consensus[coin] = {direction, count, traders, avg_notional, avg_entry}
    """
    coin_votes: dict[str, list] = {}
    for trader in traders_analysed:
        name = trader["display"]
        for pos in trader.get("positions", []):
            coin = pos["coin"]
            if coin not in coin_votes:
                coin_votes[coin] = []
            coin_votes[coin].append({
                "trader":   name,
                "address":  trader["address"],
                "side":     pos["side"],
                "notional": pos["notional"],
                "entry_px": pos["entry_px"],
                "leverage": pos["leverage"],
                "pct_acct": pos["pct_of_account"],
            })

    consensus = {}
    for coin, votes in coin_votes.items():
        if len(votes) < 2:
            continue
        longs  = [v for v in votes if v["side"] == "LONG"]
        shorts = [v for v in votes if v["side"] == "SHORT"]
        if not longs and not shorts:
            continue

        direction = "LONG" if len(longs) >= len(shorts) else "SHORT"
        aligned   = longs if direction == "LONG" else shorts
        opposed   = shorts if direction == "LONG" else longs
        agreement_pct = len(aligned) / len(votes) * 100

        total_notional = sum(v["notional"] for v in aligned)
        avg_entry      = (
            sum(v["entry_px"] * v["notional"] for v in aligned) / total_notional
            if total_notional > 0 else 0
        )

        consensus[coin] = {
            "direction":       direction,
            "aligned_count":   len(aligned),
            "opposed_count":   len(opposed),
            "total_traders":   len(votes),
            "agreement_pct":   round(agreement_pct, 1),
            "total_notional":  round(total_notional, 0),
            "avg_entry":       round(avg_entry, 4),
            "traders":         [v["trader"] for v in aligned],
            "conviction":      "HIGH" if agreement_pct >= 80 and len(aligned) >= 3 else
                               "MEDIUM" if agreement_pct >= 60 and len(aligned) >= 2 else "LOW",
        }

    # Sort by aligned_count desc
    return dict(sorted(consensus.items(), key=lambda x: x[1]["aligned_count"], reverse=True))


def run_leaderboard_scan(top_n: int = 20, deep_n: int = 10) -> dict:
    """
    Full leaderboard scan.
    top_n  = traders to fetch positions for
    deep_n = traders to also compute win rates for (slower, needs fills)
    """
    rows = fetch_leaderboard()
    ranked = rank_traders(rows, window="allTime", top_n=top_n)

    # Also get week's top performers (momentum traders)
    week_top = rank_traders(rows, window="week", top_n=10)

    # Parallel fetch: positions for all top_n, deep analysis for deep_n
    results = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(analyse_trader, t, deep=(i < deep_n)): t
            for i, t in enumerate(ranked)
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                pass

    # Sort back by allTime PnL
    results.sort(key=lambda x: x["all_time"]["pnl"], reverse=True)

    consensus = build_consensus(results)

    # Top gainers this week
    week_results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch_positions, t["address"]): t for t in week_top}
        for future in as_completed(futures):
            t = futures[future]
            try:
                t["positions"] = future.result()
                week_results.append(t)
            except Exception:
                pass

    week_consensus = build_consensus(week_results)

    # Stats summary
    win_rates = [
        t["trade_stats"]["win_rate"] for t in results
        if t.get("trade_stats") and t["trade_stats"].get("win_rate") is not None
    ]
    avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0

    return {
        "timestamp":       int(time.time()),
        "total_traders_db": len(rows),
        "top_traders":     results,
        "week_top":        week_results,
        "consensus_alltime": consensus,
        "consensus_week":    week_consensus,
        "summary": {
            "avg_win_rate_top10": round(avg_win_rate, 1),
            "total_consensus_coins": len(consensus),
            "high_conviction_plays": {
                k: v for k, v in consensus.items() if v["conviction"] == "HIGH"
            },
        },
    }
