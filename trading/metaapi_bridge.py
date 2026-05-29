"""
MetaAPI Bridge - MetaTrader 5 via MetaAPI.cloud REST API
=========================================================
Enables real MT5 trading from Linux VPS where native MT5 is unavailable.
Uses MetaAPI.cloud REST API to connect to a cloud-hosted MT5 terminal.

Prerequisites:
1. Sign up at https://metaapi.cloud
2. Add your MT5 account (investor password is enough for read-only,
   but master password is needed for trading)
3. Get API Token + Account ID from dashboard
4. Set METAAPI_TOKEN and METAAPI_ACCOUNT_ID in .env
"""
import os
import time
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime

import requests

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# MetaAPI regional base URLs
METAAPI_REGIONS = {
    "new-york": "https://mt-client-api-v1.new-york.agiliumtrade.ai",
    "london": "https://mt-client-api-v1.london.agiliumtrade.ai",
    "singapore": "https://mt-client-api-v1.singapore.agiliumtrade.ai",
    "default": "https://mt-client-api-v1.new-york.agiliumtrade.ai",
}


class MetaAPIBridge:
    """MetaTrader 5 bridge via MetaAPI.cloud (REST API)"""

    # Timeframe mapping for MetaAPI
    TIMEFRAMES = {
        "M1": "1m",
        "M5": "5m",
        "M15": "15m",
        "M30": "30m",
        "H1": "1h",
        "H4": "4h",
        "D1": "1d",
    }

    def __init__(self, token: str = None, account_id: str = None, region: str = "default"):
        self.token = token or os.getenv("METAAPI_TOKEN", "")
        self.account_id = account_id or os.getenv("METAAPI_ACCOUNT_ID", "")
        self.region = region or "default"
        self.base_url = METAAPI_REGIONS.get(self.region, METAAPI_REGIONS["default"])
        self.connected = False
        self.simulation = False  # This is REAL trading when connected
        self._account_info: Dict = {}

    def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """
        Test MetaAPI connection by fetching account info.
        Returns True if token + account_id are valid and account is reachable.
        """
        if not self.token or not self.account_id:
            logger.warning("MetaAPI: token or account_id not configured")
            self.connected = False
            return False

        try:
            info = self._fetch_account_info()
            if info:
                self._account_info = info
                self.connected = True
                self.simulation = False
                logger.info(
                    f"✅ MetaAPI connected | Account: {info.get('login')} | "
                    f"Balance: ${info.get('balance', 0):,.2f} | Server: {info.get('server')}"
                )
                return True
            else:
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"❌ MetaAPI connection error: {e}")
            self.connected = False
            return False

    def reconnect_with_credentials(self, login: int, password: str, server: str) -> Tuple[bool, str]:
        """
        MetaAPI uses token+account_id, not direct MT5 credentials.
        This method validates the stored token/account_id and returns status.
        """
        return self._test_connection()

    def _test_connection(self) -> Tuple[bool, str]:
        """Test connection and return (success, message)"""
        if not self.token or not self.account_id:
            return False, (
                "❌ MetaAPI not configured.\n\n"
                "To trade with real money on Linux VPS:\n"
                "1️⃣ Sign up at https://metaapi.cloud\n"
                "2️⃣ Add your MT5 account in the dashboard\n"
                "3️⃣ Copy your API Token and Account ID\n"
                "4️⃣ Set them in the bot via ⚙️ Trade Setup → 🔌 MetaAPI"
            )

        try:
            info = self._fetch_account_info()
            if not info:
                return False, "❌ MetaAPI account not reachable. Check token and account ID."

            mode = "🟢 REAL" if not info.get("investorMode", True) else "🔵 INVESTOR (Read-Only)"
            return True, (
                f"✅ MetaAPI Connected!\n\n"
                f"{mode} Account: {info.get('login')}\n"
                f"Server: {info.get('server')}\n"
                f"Balance: ${info.get('balance', 0):,.2f}\n"
                f"Equity: ${info.get('equity', 0):,.2f}\n\n"
                f"💡 If investor mode, you cannot place trades. "
                f"Add account with master password in MetaAPI dashboard for full trading."
            )
        except Exception as e:
            return False, f"❌ MetaAPI error: {e}"

    def disconnect(self):
        """Disconnect (no-op for REST API, but clears state)"""
        self.connected = False
        logger.info("🔌 MetaAPI disconnected")

    def is_connected(self) -> bool:
        """Check connection status"""
        return self.connected

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if self.connected and self._account_info:
            return self._account_info
        return self._fetch_account_info() or {}

    def get_balance(self) -> float:
        """Get current balance"""
        info = self.get_account_info()
        return info.get("balance", 0.0)

    def get_equity(self) -> float:
        """Get equity"""
        info = self.get_account_info()
        return info.get("equity", 0.0)

    def get_tick(self, symbol: str) -> Optional[Dict]:
        """Get current tick price"""
        url = f"{self.base_url}/users/current/accounts/{self.account_id}/symbols/{symbol}/current-price"
        try:
            resp = self._get(url)
            if not resp:
                return None
            data = resp.json()
            return {
                "bid": data.get("bid", 0),
                "ask": data.get("ask", 0),
                "spread": data.get("spread", 0),
                "time": datetime.utcnow(),
            }
        except Exception as e:
            logger.error(f"MetaAPI tick error for {symbol}: {e}")
            return None

    def get_rates(self, symbol: str, timeframe: str, count: int = 100) -> Optional[List]:
        """
        Get historical candles.
        Returns list of [time, open, high, low, close, tick_volume, spread, real_volume]
        """
        tf = self.TIMEFRAMES.get(timeframe, "15m")
        url = (
            f"{self.base_url}/users/current/accounts/{self.account_id}"
            f"/history-candles/{symbol}?timeframe={tf}&limit={count}"
        )
        try:
            resp = self._get(url)
            if not resp:
                return None
            data = resp.json()
            candles = data if isinstance(data, list) else data.get("candles", [])

            # Normalize to MT5-like format: [time, open, high, low, close, tick_volume, spread, real_volume]
            result = []
            for c in candles:
                ts = c.get("timestamp", 0)
                if isinstance(ts, str):
                    ts = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
                result.append([
                    ts,
                    c.get("open", 0),
                    c.get("high", 0),
                    c.get("low", 0),
                    c.get("close", 0),
                    c.get("tickVolume", c.get("volume", 0)),
                    c.get("spread", 0),
                    c.get("realVolume", 0),
                ])
            return result
        except Exception as e:
            logger.error(f"MetaAPI rates error for {symbol}/{timeframe}: {e}")
            return None

    def place_order(self, symbol: str, order_type: str, volume: float,
                    price: float = 0, sl: float = 0, tp: float = 0,
                    comment: str = "AI Cyber-Trader") -> Optional[int]:
        """
        Place a market order via MetaAPI.
        Returns ticket number or None.
        """
        action = "buy" if order_type.lower() == "buy" else "sell"
        url = f"{self.base_url}/users/current/accounts/{self.account_id}/trade"
        payload = {
            "symbol": symbol,
            "actionType": "ORDER_TYPE_BUY" if action == "buy" else "ORDER_TYPE_SELL",
            "volume": volume,
            "comment": comment,
        }
        if sl and sl > 0:
            payload["stopLoss"] = sl
        if tp and tp > 0:
            payload["takeProfit"] = tp

        try:
            resp = self._post(url, payload)
            if not resp:
                return None
            data = resp.json()
            ticket = data.get("positionId") or data.get("orderId")
            if ticket:
                logger.info(f"✅ MetaAPI order placed: {symbol} {action} V={volume} | Ticket=#{ticket}")
                return int(ticket)
            else:
                logger.error(f"❌ MetaAPI order failed: {data}")
                return None
        except Exception as e:
            logger.error(f"❌ MetaAPI place order error: {e}")
            return None

    def close_position(self, ticket: int, symbol: str = None, volume: float = None) -> bool:
        """Close a position by ticket ID"""
        url = f"{self.base_url}/users/current/accounts/{self.account_id}/trade"
        payload = {
            "actionType": "POSITION_CLOSE_ID",
            "positionId": str(ticket),
        }
        try:
            resp = self._post(url, payload)
            if not resp:
                return False
            data = resp.json()
            if data.get("positionId") or data.get("orderId"):
                logger.info(f"✅ MetaAPI position closed: Ticket=#{ticket}")
                return True
            else:
                logger.error(f"❌ MetaAPI close failed: {data}")
                return False
        except Exception as e:
            logger.error(f"❌ MetaAPI close error: {e}")
            return False

    def close_all_positions(self) -> int:
        """Close all open positions"""
        positions = self.get_open_positions()
        if not positions:
            return 0
        closed = 0
        for pos in positions:
            if self.close_position(pos["ticket"]):
                closed += 1
        logger.info(f"🚨 MetaAPI emergency: {closed} positions closed")
        return closed

    def get_open_positions(self) -> List[Dict]:
        """Get open positions"""
        url = f"{self.base_url}/users/current/accounts/{self.account_id}/positions"
        try:
            resp = self._get(url)
            if not resp:
                return []
            data = resp.json()
            positions = data if isinstance(data, list) else data.get("positions", [])
            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.get("id", 0),
                    "symbol": pos.get("symbol", ""),
                    "type": "buy" if pos.get("type") == "POSITION_TYPE_BUY" else "sell",
                    "volume": pos.get("volume", 0),
                    "open_price": pos.get("openPrice", 0),
                    "current_price": pos.get("price", 0),
                    "sl": pos.get("stopLoss", 0),
                    "tp": pos.get("takeProfit", 0),
                    "profit": pos.get("profit", 0),
                    "swap": pos.get("swap", 0),
                    "commission": pos.get("commission", 0),
                    "open_time": datetime.utcnow(),
                })
            return result
        except Exception as e:
            logger.error(f"MetaAPI positions error: {e}")
            return []

    def calculate_pip_value(self, symbol: str, volume: float) -> float:
        """Estimate pip value (simplified)"""
        if "XAU" in symbol or "GOLD" in symbol:
            return volume * 10
        return volume * 10

    # ─── Private REST Helpers ─────────────────────

    def _fetch_account_info(self) -> Optional[Dict]:
        """Fetch account information from MetaAPI"""
        url = f"{self.base_url}/users/current/accounts/{self.account_id}/account-information"
        resp = self._get(url)
        if not resp:
            return None
        data = resp.json()
        return {
            "login": data.get("login", 0),
            "server": data.get("server", ""),
            "balance": data.get("balance", 0.0),
            "equity": data.get("equity", 0.0),
            "margin": data.get("margin", 0.0),
            "margin_free": data.get("freeMargin", 0.0),
            "margin_level": data.get("marginLevel", 0.0),
            "currency": data.get("currency", "USD"),
            "investorMode": data.get("investorMode", False),
        }

    def _get(self, url: str, retries: int = 2) -> Optional[requests.Response]:
        """GET request with retries"""
        headers = {"auth-token": self.token, "Content-Type": "application/json"}
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    return resp
                if resp.status_code == 401:
                    logger.error("MetaAPI: Unauthorized — check your token")
                    return None
                if resp.status_code == 404:
                    logger.warning(f"MetaAPI: Not found {url}")
                    return None
                logger.warning(f"MetaAPI GET {resp.status_code}: {resp.reason}")
            except Exception as e:
                logger.warning(f"MetaAPI GET attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    time.sleep(1)
        return None

    def _post(self, url: str, payload: dict, retries: int = 2) -> Optional[requests.Response]:
        """POST request with retries"""
        headers = {"auth-token": self.token, "Content-Type": "application/json"}
        for attempt in range(retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=15)
                if resp.status_code in (200, 201, 202):
                    return resp
                if resp.status_code == 401:
                    logger.error("MetaAPI: Unauthorized — check your token")
                    return None
                logger.warning(f"MetaAPI POST {resp.status_code}: {resp.reason}")
            except Exception as e:
                logger.warning(f"MetaAPI POST attempt {attempt + 1} failed: {e}")
                if attempt < retries:
                    time.sleep(1)
        return None


# Convenience factory
def get_metaapi_bridge(token: str = None, account_id: str = None, region: str = "default") -> MetaAPIBridge:
    """Create a MetaAPIBridge instance"""
    return MetaAPIBridge(token=token, account_id=account_id, region=region)
