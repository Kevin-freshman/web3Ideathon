# roostoo_client.py
"""
(基础设施层 - 交易)
职责：只负责与 Roostoo 交易所的底层 HTTP 通信和签名。


来源参考： (Original roostoo_client2.py)
"""


import requests
import hashlib
import hmac
import time
from loguru import logger
from config import Config

class RoostooClient:
    def __init__(self):
        if not Config.ROOSTOO_API_KEY or not Config.ROOSTOO_API_SECRET:
            raise ValueError("⚠️ 请先在 .env 文件中设置 API KEY")
        self.api_key = Config.ROOSTOO_API_KEY
        self.api_secret = Config.ROOSTOO_API_SECRET
        self.session = requests.Session()
        self.session.headers.update({"RST-API-KEY": self.api_key})

    def sign(self, params: dict = None) -> str:
        params = params or {}
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()

    def _sign_and_request(self, method: str, endpoint: str, params=None, data=None):
        params = params or {}
        data = data or {}
        all_params = {**params, **data, "timestamp": int(time.time() * 1000)}
        signature = self.sign(all_params)

        headers = {
            "RST-API-KEY": self.api_key,
            "MSG-SIGNATURE": signature,
        }
        url = Config.BASE_URL + endpoint
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=all_params, headers=headers)
            else:
                response = self.session.post(url, data=all_params, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API 请求失败: {endpoint} | {str(e)}")
            raise

    # ... (此处保留原有 get_balance, place_order 等方法，代码逻辑不变) ...
    # 为节省篇幅，这里假设原有方法的实现与  一致
    def get_exchange_info(self):
        return self._sign_and_request("GET", "/v3/exchangeInfo")
        
    def get_balance(self) -> dict:
        resp = self._sign_and_request("GET", "/v3/balance")
        if resp and resp.get("Success"):
            wallet = resp.get("Wallet", {})
            return {coin: info.get("Free", 0) for coin, info in wallet.items()}
        return {}

    def place_order(self, pair: str, side: str, quantity: float, price: float = None) -> dict:
        payload = {
            "pair": pair,
            "side": side.upper(),
            "quantity": float(quantity),
            "type": "MARKET" if price is None else "LIMIT"
        }
        if price is not None: payload["price"] = float(price)
        return self._sign_and_request("POST", "/v3/place_order", data=payload)