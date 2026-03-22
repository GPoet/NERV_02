#!/usr/bin/env python3
from __future__ import annotations
"""
hl_trader.py — Hyperliquid trade executor.

Parses natural-language-ish trade commands and executes them.

Usage:
    python trader.py "BUY BTC 0.01"              # market buy 0.01 BTC
    python trader.py "SELL ETH 0.5"              # market sell 0.5 ETH
    python trader.py "BUY BTC 0.01 limit 90000"  # limit buy @ $90k
    python trader.py "CLOSE BTC"                 # close entire BTC position
    python trader.py "CLOSE ETH 0.25"            # partial close 0.25 ETH
    python trader.py "CANCEL BTC"                # cancel all open BTC orders
    python trader.py "LEVERAGE BTC 5"            # set BTC leverage to 5x
    python trader.py "STATUS"                    # show account summary

Env vars (required for trading):
    HL_PRIVATE_KEY       — private key hex (0x...)
    HL_WALLET_ADDRESS    — wallet address (optional, derived from key if absent)
"""
import sys
import json
import argparse

import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
sys.path.insert(0, _os.path.dirname(_here))
from hl.client import get_exchange, get_clearinghouse_state, wallet_address


DEFAULT_SLIPPAGE = 0.005  # 0.5%


def parse_command(args_list: list[str]) -> dict:
    """Parse trade command from argv tokens."""
    if not args_list:
        raise ValueError("No command provided")

    cmd = args_list[0].upper()
    tokens = args_list[1:]

    if cmd == "STATUS":
        return {"action": "status"}

    if cmd in ("BUY", "SELL"):
        if len(tokens) < 2:
            raise ValueError(f"{cmd} requires: COIN SIZE [limit PRICE] [sl PRICE] [tp PRICE]")
        coin = tokens[0].upper()
        size = float(tokens[1])
        is_buy = cmd == "BUY"
        price = None
        order_type = "market"
        sl_px = None
        tp_px = None

        i = 2
        while i < len(tokens):
            t = tokens[i].lower()
            if t == "limit" and i + 1 < len(tokens):
                order_type = "limit"
                price = float(tokens[i + 1])
                i += 2
            elif t == "sl" and i + 1 < len(tokens):
                sl_px = float(tokens[i + 1])
                i += 2
            elif t == "tp" and i + 1 < len(tokens):
                tp_px = float(tokens[i + 1])
                i += 2
            else:
                i += 1

        return {
            "action": "open",
            "coin": coin,
            "is_buy": is_buy,
            "size": size,
            "order_type": order_type,
            "price": price,
            "sl_px": sl_px,
            "tp_px": tp_px,
        }

    if cmd == "CLOSE":
        if not tokens:
            raise ValueError("CLOSE requires: COIN [SIZE]")
        coin = tokens[0].upper()
        size = float(tokens[1]) if len(tokens) > 1 else None
        return {"action": "close", "coin": coin, "size": size}

    if cmd == "CANCEL":
        coin = tokens[0].upper() if tokens else None
        return {"action": "cancel", "coin": coin}

    if cmd == "LEVERAGE":
        if len(tokens) < 2:
            raise ValueError("LEVERAGE requires: COIN VALUE [cross|isolated]")
        coin = tokens[0].upper()
        lev = int(tokens[1])
        is_cross = (tokens[2].lower() == "cross") if len(tokens) > 2 else True
        return {"action": "leverage", "coin": coin, "leverage": lev, "is_cross": is_cross}

    if cmd == "TWAP":
        # TWAP BTC BUY 1.0 minutes 60
        if len(tokens) < 4:
            raise ValueError("TWAP requires: COIN BUY|SELL SIZE minutes DURATION")
        coin = tokens[0].upper()
        is_buy = tokens[1].upper() == "BUY"
        size = float(tokens[2])
        minutes = int(tokens[4]) if len(tokens) > 4 and tokens[3].lower() == "minutes" else (int(tokens[3]) if len(tokens) > 3 and tokens[3].isdigit() else 60)
        return {"action": "twap", "coin": coin, "is_buy": is_buy, "size": size, "minutes": minutes}

    raise ValueError(f"Unknown command: {cmd}. Valid: BUY, SELL, CLOSE, CANCEL, LEVERAGE, TWAP, STATUS")


def execute_trade(cmd: dict, dry_run: bool = False) -> dict:
    action = cmd["action"]

    if action == "status":
        addr = wallet_address()
        state = get_clearinghouse_state(addr)
        ms = state.get("marginSummary", {})
        return {
            "ok": True,
            "account_value": float(ms.get("accountValue", 0)),
            "margin_used": float(ms.get("totalMarginUsed", 0)),
            "unrealized_pnl": float(ms.get("totalUnrealizedPnl", 0)),
            "withdrawable": float(state.get("withdrawable", 0)),
            "positions": len([p for p in state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]),
        }

    if dry_run:
        return {"ok": True, "dry_run": True, "command": cmd}

    exchange, addr = get_exchange()

    if action == "open":
        coin = cmd["coin"]
        is_buy = cmd["is_buy"]
        size = cmd["size"]

        if cmd["order_type"] == "market":
            result = exchange.market_open(coin, is_buy, size, slippage=DEFAULT_SLIPPAGE)
        else:
            price = cmd["price"]
            result = exchange.order(coin, is_buy, size, price, {"limit": {"tif": "Gtc"}})

        response = {"ok": True, "action": "open", "result": result}

        # Place stop-loss if specified
        if cmd.get("sl_px"):
            sl_result = exchange.order(
                coin, not is_buy, size, cmd["sl_px"],
                {"trigger": {"isMarket": True, "tpsl": "sl", "triggerPx": str(cmd["sl_px"])}},
                reduce_only=True,
            )
            response["sl_result"] = sl_result

        # Place take-profit if specified
        if cmd.get("tp_px"):
            tp_result = exchange.order(
                coin, not is_buy, size, cmd["tp_px"],
                {"trigger": {"isMarket": True, "tpsl": "tp", "triggerPx": str(cmd["tp_px"])}},
                reduce_only=True,
            )
            response["tp_result"] = tp_result

        return response

    if action == "close":
        coin = cmd["coin"]
        size = cmd.get("size")  # None = close all
        result = exchange.market_close(coin, sz=size, slippage=DEFAULT_SLIPPAGE)
        return {"ok": True, "action": "close", "result": result}

    if action == "cancel":
        coin = cmd.get("coin")
        from hl.client import get_open_orders
        open_orders = get_open_orders(addr)
        if coin:
            to_cancel = [o for o in open_orders if o.get("coin") == coin]
        else:
            to_cancel = open_orders

        if not to_cancel:
            return {"ok": True, "action": "cancel", "cancelled": 0, "message": "No open orders found"}

        cancel_requests = [{"coin": o["coin"], "oid": o["oid"]} for o in to_cancel]
        result = exchange.bulk_cancel(cancel_requests)
        return {"ok": True, "action": "cancel", "cancelled": len(cancel_requests), "result": result}

    if action == "leverage":
        result = exchange.update_leverage(cmd["leverage"], cmd["coin"], cmd["is_cross"])
        return {"ok": True, "action": "leverage", "result": result}

    if action == "twap":
        result = exchange.order(
            cmd["coin"], cmd["is_buy"], cmd["size"], None,
            {"twap": {"minutes": cmd["minutes"], "randomize": False}},
        )
        return {"ok": True, "action": "twap", "result": result}

    raise ValueError(f"Unknown action: {action}")


def format_result(cmd: dict, result: dict) -> str:
    if not result.get("ok"):
        return f"❌ Trade FAILED: {result}"

    action = cmd.get("action", "")

    if action == "status":
        return (
            f"Account: ${result['account_value']:,.2f} | "
            f"Margin used: ${result['margin_used']:,.2f} | "
            f"PnL: {'+' if result['unrealized_pnl'] >= 0 else ''}${result['unrealized_pnl']:,.2f} | "
            f"{result['positions']} positions open"
        )

    if result.get("dry_run"):
        return f"DRY RUN: would execute {json.dumps(cmd)}"

    raw = result.get("result", {})
    if isinstance(raw, dict):
        status = raw.get("status", "?")
        resp = raw.get("response", {})
        if status == "ok":
            data = resp.get("data", {})
            filled = data.get("statuses", [{}])[0] if data.get("statuses") else {}
            if filled.get("filled"):
                f = filled["filled"]
                return (
                    f"✅ {action.upper()} executed | "
                    f"Total size: {f.get('totalSz', '?')} @ avg ${float(f.get('avgPx', 0)):,.4g}"
                )
            elif filled.get("resting"):
                r = filled["resting"]
                return f"✅ Order resting | OID: {r.get('oid')} | Size: {r.get('sz')} @ ${r.get('limitPx')}"
            else:
                return f"✅ {action.upper()} submitted: {json.dumps(data)[:200]}"
        else:
            return f"❌ Error: {raw}"
    return f"✅ Done: {json.dumps(result)[:300]}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid trade executor")
    parser.add_argument("command", nargs="+", help="Trade command tokens")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't execute")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    try:
        cmd = parse_command(args.command)
        result = execute_trade(cmd, dry_run=args.dry_run)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_result(cmd, result))
