"""
Hyperliquid base client — shared setup for all HL scripts.
Reads HL_PRIVATE_KEY and HL_WALLET_ADDRESS from environment.
"""
import os
import sys
import json
import urllib.request
import urllib.error
from typing import Any

MAINNET = "https://api.hyperliquid.xyz"
TESTNET = "https://api.hyperliquid-testnet.xyz"

BASE_URL = os.environ.get("HL_BASE_URL", MAINNET)


def _post(endpoint: str, payload: dict) -> Any:
    url = f"{BASE_URL}/{endpoint}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {body}") from e


# ── Info queries ─────────────────────────────────────────────────────────────

def get_all_mids() -> dict:
    return _post("info", {"type": "allMids"})


def get_meta_and_asset_ctxs() -> list:
    """Returns [meta_universe, asset_contexts] for all perps."""
    return _post("info", {"type": "metaAndAssetCtxs"})


def get_spot_meta_and_asset_ctxs() -> list:
    """Returns [spot_meta, spot_asset_contexts]."""
    return _post("info", {"type": "spotMetaAndAssetCtxs"})


def get_clearinghouse_state(address: str) -> dict:
    """Full position state: margins, positions, account value."""
    return _post("info", {"type": "clearinghouseState", "user": address.lower()})


def get_spot_state(address: str) -> dict:
    return _post("info", {"type": "spotClearinghouseState", "user": address.lower()})


def get_open_orders(address: str) -> list:
    return _post("info", {"type": "openOrders", "user": address.lower()})


def get_user_fills(address: str) -> list:
    return _post("info", {"type": "userFills", "user": address.lower()})


def get_funding_history(coin: str, start_ms: int, end_ms: int | None = None) -> list:
    payload: dict = {"type": "fundingHistory", "coin": coin, "startTime": start_ms}
    if end_ms:
        payload["endTime"] = end_ms
    return _post("info", payload)


def get_predicted_fundings() -> list:
    return _post("info", {"type": "predictedFundings"})


def get_l2_book(coin: str, n_sig_figs: int = 5) -> dict:
    return _post("info", {"type": "l2Book", "coin": coin, "nSigFigs": n_sig_figs})


def get_candles(coin: str, interval: str, start_ms: int, end_ms: int | None = None) -> list:
    payload: dict = {
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": interval, "startTime": start_ms},
    }
    if end_ms:
        payload["req"]["endTime"] = end_ms
    return _post("info", payload)


def get_user_fees(address: str) -> dict:
    return _post("info", {"type": "userFees", "user": address.lower()})


def get_user_funding(address: str, start_ms: int) -> list:
    return _post("info", {"type": "userFunding", "user": address.lower(), "startTime": start_ms})


def get_portfolio(address: str) -> list:
    return _post("info", {"type": "portfolio", "user": address.lower()})


# ── Exchange actions (require private key) ────────────────────────────────────

def get_exchange():
    """Lazy-load Exchange — only when trading is needed."""
    try:
        from eth_account import Account as EthAccount
        from hyperliquid.exchange import Exchange
        from hyperliquid.utils import constants
    except ImportError:
        print("ERROR: hyperliquid-python-sdk not installed. Run: pip install hyperliquid-python-sdk", file=sys.stderr)
        sys.exit(1)

    private_key = os.environ.get("HL_PRIVATE_KEY")
    if not private_key:
        print("ERROR: HL_PRIVATE_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    account = EthAccount.from_key(private_key)
    wallet_address = os.environ.get("HL_WALLET_ADDRESS", account.address)
    base_url = BASE_URL.replace("/exchange", "")
    exchange = Exchange(account, base_url, account_address=wallet_address)
    return exchange, wallet_address


def wallet_address() -> str:
    addr = os.environ.get("HL_WALLET_ADDRESS")
    if not addr:
        try:
            from eth_account import Account as EthAccount
            pk = os.environ.get("HL_PRIVATE_KEY", "")
            if pk:
                addr = EthAccount.from_key(pk).address
        except Exception:
            pass
    if not addr:
        print("ERROR: HL_WALLET_ADDRESS or HL_PRIVATE_KEY required.", file=sys.stderr)
        sys.exit(1)
    return addr
