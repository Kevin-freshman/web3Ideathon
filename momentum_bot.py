# momentum_bot.py
"""

 (策略层)职责：包含具体的策略算法。它只关心“计算目标持仓”和“生成调仓指令”，不直接处理 HTTP 请求。
 来源参考：7 (DynamicMomentumBot 类)数学公式（动量计算）：
 $$\text{Target Position} = (\frac{P_{t}}{P_{t-1}} - 1) \times \text{Base Allocation}$$
"""



import time
import math
from loguru import logger
from config import Config
from risk_manager import RiskManager
from exchange_service import ExchangeService

class MomentumBot:
    def __init__(self, service: ExchangeService, initial_cash: float):
        self.service = service
        self.risk = RiskManager(initial_cash)
        self.initial_cash = initial_cash

    def calculate_momentum_target(self, symbol, current_usd):
        """计算单个币种的目标持仓"""
        asset = symbol.split("/")[0]
        try:
            # 获取最近2小时数据计算动量
            data = self.service.horus.get_market_price(asset=asset, interval="1h", limit=2)
            if len(data) >= 2:
                ret = (data[1]["price"] / data[0]["price"]) - 1
                target_usd = ret * Config.BASE_PER_PERCENT
                return max(target_usd, -current_usd * 0.5) # 简单止损逻辑
        except Exception as e:
            logger.error(f"{symbol} 动量计算错误: {e}")
        return 0

    def rebalance(self, current_prices, balance, total_value):
        """执行再平衡逻辑"""
        usd = balance.get("USD", 0)
        
        for sym in Config.SYMBOLS:
            if sym not in self.service.trade_rules: continue
            
            # 1. 计算目标
            target_usd = self.calculate_momentum_target(sym, usd)
            if target_usd == 0: continue

            # 2. 计算差额
            asset = sym.split("/")[0]
            current_pos_val = balance.get(asset, 0) * current_prices[sym]
            diff_usd = target_usd - current_pos_val

            # 3. 仓位限制 (Max 35%)
            max_allowed = total_value * 0.35
            if current_pos_val + diff_usd > max_allowed:
                diff_usd = max_allowed - current_pos_val

            # 4. 下单计算
            price = current_prices[sym]
            amount = diff_usd / price
            
            # 规则修正 (精度、步长)
            rule = self.service.trade_rules[sym]
            step = rule["step_size"]
            amount = math.floor(amount / step) * step
            amount = round(amount, rule["qty_precision"])

            # 5. 执行
            if abs(diff_usd) > 50 and abs(amount) > 0:
                side = "BUY" if amount > 0 else "SELL"
                self.service.place_order(sym, side, abs(amount))
                logger.info(f"→ {side} {abs(amount)} {sym} (${abs(diff_usd):.0f})")

    def step(self):
        try:
            # 1. 数据准备
            prices = {sym: self.service.fetch_price(sym) for sym in Config.SYMBOLS}
            balance = self.service.get_flattened_balance()
            
            # 计算总价值
            usd = balance.get("USD", 0)
            positions = {}
            for sym in Config.SYMBOLS:
                asset = sym.split("/")[0]
                positions[sym] = balance.get(asset, 0) * prices.get(sym, 0)
            
            total_value = usd + sum(positions.values())
            logger.info(f"总资产: ${total_value:,.0f}")

            # 2. 风控
            if not self.risk.check(total_value, positions):
                return

            # 3. 执行策略
            self.rebalance(prices, balance, total_value)

        except Exception as e:
            logger.error(f"策略循环错误: {e}", exc_info=True)

    def run(self):
        logger.info("策略启动...")
        while True:
            self.step()
            time.sleep(Config.INTERVAL)