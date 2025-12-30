# bollinger_bot.py
"""
(策略层) 职责：布林带 (Bollinger Bands) 均值回归策略。
数学公式：
- 中轨 (MB) = N日收盘价的简单移动平均 (SMA)
- 上轨 (UP) = MB + k * 标准差 (StdDev)
- 下轨 (DN) = MB - k * 标准差 (StdDev)
"""

import time
import math
import statistics
from loguru import logger
from config import Config
from risk_manager import RiskManager
from exchange_service import ExchangeService

class BollingerBot:
    def __init__(self, service: ExchangeService, initial_cash: float):
        self.service = service
        self.risk = RiskManager(initial_cash)
        self.initial_cash = initial_cash
        # 策略参数
        self.period = 20    # 20周期均线
        self.k = 2          # 2倍标准差

    def calculate_bb_signal(self, symbol):
        """
        计算布林带信号
        返回: 
            1: 价格跌破下轨 (超卖，买入机会)
           -1: 价格突破上轨 (超买，卖出机会)
            0: 震荡区间内 (持有或不操作)
        """
        asset = symbol.split("/")[0]
        try:
            # 获取足够计算布林带的数据
            data = self.service.horus.get_market_price(asset=asset, interval="1h", limit=self.period)
            if len(data) < self.period:
                return 0

            prices = [d["price"] for d in data]
            current_price = prices[-1]

            # 1. 计算中轨 (SMA)
            ma = sum(prices) / self.period
            
            # 2. 计算标准差
            std_dev = statistics.stdev(prices)
            
            # 3. 计算上下轨
            upper_band = ma + (self.k * std_dev)
            lower_band = ma - (self.k * std_dev)

            # 4. 信号判定
            if current_price < lower_band:
                return 1  # 触底反弹逻辑：买入
            elif current_price > upper_band:
                return -1 # 触顶回落逻辑：卖出
                
        except Exception as e:
            logger.error(f"{symbol} 布林带计算错误: {e}")
        return 0

    def rebalance(self, current_prices, balance, total_value):
        """执行调仓逻辑"""
        for sym in Config.SYMBOLS:
            if sym not in self.service.trade_rules: continue
            
            signal = self.calculate_bb_signal(sym)
            if signal == 0: continue

            asset = sym.split("/")[0]
            current_pos_qty = balance.get(asset, 0)
            current_pos_val = current_pos_qty * current_prices[sym]
            
            diff_usd = 0
            if signal == 1: # 买入信号：加仓至固定比例
                target_val = total_value * 0.25 # 假设单币种目标仓位 25%
                diff_usd = target_val - current_pos_val
            elif signal == -1: # 卖出信号：减仓或清仓
                diff_usd = -current_pos_val

            # 精度处理与执行
            price = current_prices[sym]
            amount = diff_usd / price
            rule = self.service.trade_rules[sym]
            amount = math.floor(abs(amount) / rule["step_size"]) * rule["step_size"] * (1 if diff_usd > 0 else -1)
            amount = round(amount, rule["qty_precision"])

            if abs(amount * price) > 20: # 交易阈值
                side = "BUY" if amount > 0 else "SELL"
                self.service.place_order(sym, side, abs(amount))
                logger.info(f"【Bollinger {side}】{sym} | 价格: {price} | 金额: ${abs(amount*price):.0f}")

    def step(self):
        try:
            prices = {sym: self.service.fetch_price(sym) for sym in Config.SYMBOLS}
            balance = self.service.get_flattened_balance()
            
            # 计算账户净值
            usd = balance.get("USD", 0)
            positions = {sym: balance.get(sym.split("/")[0], 0) * prices[sym] for sym in Config.SYMBOLS}
            total_value = usd + sum(positions.values())
            
            logger.info(f"BB策略运行中 | 总资产: ${total_value:,.2f}")

            if self.risk.check(total_value, positions):
                self.rebalance(prices, balance, total_value)

        except Exception as e:
            logger.error(f"BB策略循环异常: {e}")

    def run(self):
        logger.info("布林带均值回归策略启动...")
        while True:
            self.step()
            time.sleep(Config.INTERVAL)