# exchange_service.py
"""
(服务层 - 聚合)
职责：这个类是原有 kz_bot4.py 中 ExchangeClient 的升级版。它作为 Facade (门面模式)，将交易和行情数据整合，并处理交易规则（精度、步长）的加载。


来源参考： (原 ExchangeClient 逻辑)
"""


from datetime import datetime
from loguru import logger
from roostoo_client import RoostooClient
from horus_client import HorusClient
from config import Config

class ExchangeService:
    def __init__(self):
        self.roostoo = RoostooClient()
        self.horus = HorusClient()
        self.trade_rules = self._load_trade_rules()
        logger.info(f"客户端就绪 | DRY_RUN={Config.DRY_RUN}")

    def fetch_price(self, symbol: str) -> float:
        """聚合：从 Horus 获取价格，失败则降级"""
        try:
            asset = symbol.split("/")[0]
            price = self.horus.get_latest_price(asset)
            return price
        except Exception as e:
            logger.warning(f"{symbol} 获取失败: {e}")
            return 0.0

    def get_flattened_balance(self):
        """聚合：将 Roostoo 的余额格式化为简单字典"""
        raw_balance = self.roostoo.get_balance()
        # 原有逻辑已经由 roostoo_client 处理了部分，这里直接返回或进一步处理
        return raw_balance

    def place_order(self, symbol: str, side: str, amount: float):
        if amount == 0: return
        if Config.DRY_RUN:
            logger.info(f"[DRY] 模拟 {side} {abs(amount):.6f} {symbol}")
            return {"status": "filled"}
        try:
            return self.roostoo.place_order(symbol, side, abs(amount))
        except Exception as e:
            logger.error(f"下单失败 {symbol}: {e}")

    def _load_trade_rules(self):
        """加载交易精度规则"""
        info = self.roostoo.get_exchange_info()
        rules = {}
        if not info or "TradePairs" not in info:
            return rules
            
        for symbol, conf in info["TradePairs"].items():
            qty_precision = conf.get("AmountPrecision", 0)
            rules[symbol] = {
                "step_size": float(10 ** (-qty_precision)),
                "qty_precision": qty_precision,
            }
        return rules