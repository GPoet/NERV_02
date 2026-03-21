#!/usr/bin/env python3
"""
Macro intelligence layer — crypto-native macro signals.

Sources:
  - CoinGecko global (BTC dominance, total market cap, volume, alts)
  - Alternative.me Fear & Greed index
  - CoinGecko trending coins (social momentum)
  - BTC price relative to key MAs (market regime)
  - Altcoin season index
  - ETH/BTC ratio (rotation signal)

No API keys needed — all public endpoints.
"""
import json
import time
import urllib.request
import urllib.error
from typing import Any


def _fetch(url: str, timeout: int = 12) -> Any:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            # Rate limited — wait 3s and retry once
            time.sleep(3)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        raise


def get_global_metrics() -> dict:
    """CoinGecko global market metrics."""
    try:
        data = _fetch("https://api.coingecko.com/api/v3/global")
        g = data.get("data", {})
        return {
            "total_market_cap_usd":   g.get("total_market_cap", {}).get("usd", 0),
            "total_volume_24h_usd":   g.get("total_volume", {}).get("usd", 0),
            "btc_dominance_pct":      round(g.get("market_cap_percentage", {}).get("btc", 0), 2),
            "eth_dominance_pct":      round(g.get("market_cap_percentage", {}).get("eth", 0), 2),
            "market_cap_change_24h":  round(g.get("market_cap_change_percentage_24h_usd", 0), 2),
            "active_coins":           g.get("active_cryptocurrencies", 0),
        }
    except Exception as e:
        return {"error": str(e)}


def get_fear_greed() -> dict:
    """Alternative.me Fear & Greed index — 0 (extreme fear) to 100 (extreme greed)."""
    try:
        data = _fetch("https://api.alternative.me/fng/?limit=3")
        entries = data.get("data", [])
        current = entries[0] if entries else {}
        yesterday = entries[1] if len(entries) > 1 else {}
        last_week = entries[2] if len(entries) > 2 else {}

        val = int(current.get("value", 50))
        cls = current.get("value_classification", "?")

        # Interpretation for trading
        if val <= 20:
            signal = "EXTREME_FEAR → contrarian LONG setup"
        elif val <= 35:
            signal = "FEAR → cautious accumulation zone"
        elif val <= 55:
            signal = "NEUTRAL → wait for directional bias"
        elif val <= 75:
            signal = "GREED → momentum ok, tighten stops"
        else:
            signal = "EXTREME_GREED → reduce longs, short setups forming"

        return {
            "value":            val,
            "classification":   cls,
            "signal":           signal,
            "yesterday":        int(yesterday.get("value", 50)),
            "last_week":        int(last_week.get("value", 50)),
            "trend":            "RISING" if val > int(yesterday.get("value", 50)) else "FALLING",
        }
    except Exception as e:
        return {"error": str(e), "value": 50, "signal": "DATA_UNAVAILABLE"}


def get_trending_coins() -> list[dict]:
    """CoinGecko trending — top 7 coins by search volume (social momentum)."""
    try:
        data = _fetch("https://api.coingecko.com/api/v3/search/trending")
        coins = data.get("coins", [])
        return [
            {
                "name":   c["item"]["name"],
                "symbol": c["item"]["symbol"].upper(),
                "rank":   c["item"].get("market_cap_rank", 9999),
                "score":  c["item"].get("score", 0),
            }
            for c in coins[:7]
        ]
    except Exception:
        return []


def get_btc_price_metrics() -> dict:
    """BTC key prices for market regime detection."""
    try:
        # Current price + 24h/7d/30d change
        data = _fetch(
            "https://api.coingecko.com/api/v3/simple/price"
            "?ids=bitcoin,ethereum,solana"
            "&vs_currencies=usd"
            "&include_24hr_change=true"
            "&include_7d_change=true"
            "&include_30d_change=true"
            "&include_24hr_vol=true"
            "&include_market_cap=true"
        )
        btc = data.get("bitcoin", {})
        eth = data.get("ethereum", {})
        sol = data.get("solana", {})

        btc_px = btc.get("usd", 0)
        eth_px = eth.get("usd", 0)
        sol_px = sol.get("usd", 0)

        # ETH/BTC ratio — above 0.05 = ETH outperforming (alt season signal)
        eth_btc = eth_px / btc_px if btc_px > 0 else 0

        # 30-day trend
        btc_30d = btc.get("usd_30d_change", 0) or 0
        if btc_30d > 20:
            regime = "BULL_TREND"
        elif btc_30d > 5:
            regime = "MILD_UPTREND"
        elif btc_30d > -5:
            regime = "SIDEWAYS"
        elif btc_30d > -20:
            regime = "MILD_DOWNTREND"
        else:
            regime = "BEAR_TREND"

        # Alt season: if ETH and SOL outperforming BTC 30d → alt season
        eth_30d = eth.get("usd_30d_change", 0) or 0
        sol_30d = sol.get("usd_30d_change", 0) or 0
        alt_season = eth_30d > btc_30d + 10 and sol_30d > btc_30d + 10

        return {
            "btc_price":       btc_px,
            "eth_price":       eth_px,
            "sol_price":       sol_px,
            "eth_btc_ratio":   round(eth_btc, 5),
            "btc_24h_pct":     round(btc.get("usd_24h_change", 0) or 0, 2),
            "btc_7d_pct":      round(btc.get("usd_7d_change", 0) or 0, 2),
            "btc_30d_pct":     round(btc_30d, 2),
            "eth_30d_pct":     round(eth_30d, 2),
            "sol_30d_pct":     round(sol_30d, 2),
            "market_regime":   regime,
            "alt_season":      alt_season,
            "btc_vol_24h":     btc.get("usd_24h_vol", 0),
            "btc_mcap":        btc.get("usd_market_cap", 0),
        }
    except Exception as e:
        return {"error": str(e)}


def get_top_movers() -> dict:
    """Top gainers and losers by market cap (coingecko top250)."""
    try:
        data = _fetch(
            "https://api.coingecko.com/api/v3/coins/markets"
            "?vs_currency=usd&order=market_cap_desc&per_page=100"
            "&page=1&price_change_percentage=24h,7d"
        )
        gainers = sorted(data, key=lambda x: x.get("price_change_percentage_24h") or 0, reverse=True)[:5]
        losers  = sorted(data, key=lambda x: x.get("price_change_percentage_24h") or 0)[:5]
        return {
            "top_gainers": [
                {"symbol": c["symbol"].upper(), "change_24h": round(c.get("price_change_percentage_24h") or 0, 2), "price": c["current_price"]}
                for c in gainers
            ],
            "top_losers": [
                {"symbol": c["symbol"].upper(), "change_24h": round(c.get("price_change_percentage_24h") or 0, 2), "price": c["current_price"]}
                for c in losers
            ],
        }
    except Exception:
        return {"top_gainers": [], "top_losers": []}


def run_macro_scan() -> dict:
    """Run all macro data fetches and return unified report."""
    global_m  = get_global_metrics()
    fear_greed = get_fear_greed()
    trending  = get_trending_coins()
    btc_m     = get_btc_price_metrics()
    movers    = get_top_movers()

    # Derive overall market bias
    fg_val = fear_greed.get("value", 50)
    regime = btc_m.get("market_regime", "SIDEWAYS")
    btc_24h = btc_m.get("btc_24h_pct", 0)
    dom = global_m.get("btc_dominance_pct", 50)

    # Market bias scoring (-2 to +2)
    bias = 0
    if regime in ("BULL_TREND", "MILD_UPTREND"): bias += 1
    if regime in ("BEAR_TREND", "MILD_DOWNTREND"): bias -= 1
    if fg_val < 30: bias += 0.5   # fear = contrarian long
    if fg_val > 75: bias -= 0.5   # greed = contrarian short
    if btc_24h > 3: bias += 0.5
    if btc_24h < -3: bias -= 0.5

    if bias >= 1:
        overall_bias = "RISK_ON"
        bias_note = "Macro supports long positions"
    elif bias <= -1:
        overall_bias = "RISK_OFF"
        bias_note = "Macro favors short or defensive positioning"
    else:
        overall_bias = "NEUTRAL"
        bias_note = "Mixed macro signals — wait for clarity"

    # BTC dominance signal
    if dom > 58:
        dom_signal = "BTC_SEASON — capital concentrated in BTC, alts underperform"
    elif dom < 45:
        dom_signal = "ALT_SEASON — capital flowing to alts, levered alt longs favored"
    else:
        dom_signal = "TRANSITION — watch BTC.D direction for rotation signal"

    return {
        "timestamp":      int(time.time()),
        "global":         global_m,
        "fear_greed":     fear_greed,
        "btc_metrics":    btc_m,
        "trending":       trending,
        "movers":         movers,
        "derived": {
            "overall_bias":    overall_bias,
            "bias_score":      round(bias, 1),
            "bias_note":       bias_note,
            "dom_signal":      dom_signal,
            "alt_season":      btc_m.get("alt_season", False),
        },
    }


if __name__ == "__main__":
    import sys, argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_macro_scan()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        d = result["derived"]
        fg = result["fear_greed"]
        btc = result["btc_metrics"]
        g = result["global"]
        print(f"=== MACRO SCAN ===")
        print(f"Bias: {d['overall_bias']} (score {d['bias_score']}) — {d['bias_note']}")
        print(f"Regime: {btc.get('market_regime')} | BTC 24h: {btc.get('btc_24h_pct'):+.1f}% | 30d: {btc.get('btc_30d_pct'):+.1f}%")
        print(f"Fear/Greed: {fg.get('value')} ({fg.get('classification')}) | Trend: {fg.get('trend')}")
        print(f"BTC Dom: {g.get('btc_dominance_pct')}% → {d['dom_signal']}")
        print(f"Total MCap: ${g.get('total_market_cap_usd', 0)/1e12:.2f}T | 24h chg: {g.get('market_cap_change_24h'):+.1f}%")
        print(f"Alt season: {btc.get('alt_season')}")
        if result["trending"]:
            print(f"Trending: {', '.join(c['symbol'] for c in result['trending'])}")
