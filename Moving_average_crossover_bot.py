# ma_crossover_bot.py
"""
(策略层) 职责：双均线金叉死叉策略。
信号逻辑：
- 金叉 (Golden Cross): 短期 MA 上穿 长期 MA -> 买入信号
- 死叉 (Death Cross): 短期 MA 下穿 长期 MA -> 卖出信号
"""

import time
import math
from loguru import logger
from config import Config
from risk_manager import RiskManager
from exchange_service import ExchangeService

class MACrossoverBot:
    def __init__(self, service: ExchangeService, initial_cash: float):
        self.service = service
        self.risk = RiskManager(initial_cash)
        self.initial_cash = initial_cash
        # 定义均线周期
        self.fast_period = 7
        self.slow_period = 25

    def calculate_ma_signal(self, symbol):
        """
        计算均线信号
        返回: 1 (买入), -1 (卖出), 0 (持有/观望)
        """
        asset = symbol.split("/")[0]
        try:
            # 获取足够计算慢线的数据量 (需包含当前点和前一点以判断交叉)
            limit = self.slow_period + 2
            data = self.service.horus.get_market_price(asset=asset, interval="1h", limit=limit)
            
            if len(data) < limit:
                logger.warning(f"{symbol} 数据不足，跳过计算")
                return 0

            # 提取价格列表
            prices = [d["price"] for d in data]
            
            # 计算当前时刻的 MA
            ma_fast_curr = sum(prices[-self.fast_period:]) / self.fast_period
            ma_slow_curr = sum(prices[-self.slow_period:]) / self.slow_period
            
            # 计算上一时刻的 MA (用于判断“交叉”动作)
            ma_fast_prev = sum(prices[-self.fast_period-1:-1]) / self.fast_period
            ma_slow_prev = sum(prices[-self.slow_period-1:-1]) / self.slow_period

            # 判定逻辑
            if ma_fast_prev <= ma_slow_prev and ma_fast_curr > ma_slow_curr:
                return 1  # 金叉
            elif ma_fast_prev >= ma_slow_prev and ma_fast_curr < ma_slow_curr:
                return -1 # 死叉
                
        except Exception as e:
            logger.error(f"{symbol} 均线计算错误: {e}")
        return 0

    def rebalance(self, current_prices, balance, total_value):
        """执行再平衡逻辑"""
        for sym in Config.SYMBOLS:
            if sym not in self.service.trade_rules: continue
            
            # 1. 获取交叉信号
            signal = self.calculate_ma_signal(sym)
            if signal == 0: continue # 无交叉信号，不操作

            # 2. 计算目标差额
            asset = sym.split("/")[0]
            current_pos_qty = balance.get(asset, 0)
            current_pos_val = current_pos_qty * current_prices[sym]
            
            diff_usd = 0
            if signal == 1: # 金叉：目标是买入到预设仓位（例如总资产的30%）
                target_val = total_value * 0.30 
                diff_usd = target_val - current_pos_val
            elif signal == -1: # 死叉：目标是清仓
                diff_usd = -current_pos_val

            # 3. 仓位风控限制 (最大 35%)
            if signal == 1:
                max_allowed = total_value * 0.35
                if current_pos_val + diff_usd > max_allowed:
                    diff_usd = max_allowed - current_pos_val

            # 4. 下单量计算
            price = current_prices[sym]
            amount = diff_usd / price
            
            # 规则修正 (精度、步长)
            rule = self.service.trade_rules[sym]
            step = rule["step_size"]
            # 使用 math.floor 避免买入超额，卖出时直接使用绝对值
            amount = math.floor(abs(amount) / step) * step * (1 if amount > 0 else -1)
            amount = round(amount, rule["qty_precision"])

            # 5. 执行下单 (最小成交金额 10 USD)
            if abs(amount * price) > 10:
                side = "BUY" if amount > 0 else "SELL"
                self.service.place_order(sym, side, abs(amount))
                logger.info(f"【{side} 信号】{sym} 数量: {abs(amount)} 价值: ${abs(diff_usd):.2f}")

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
            logger.info(f"当前总资产: ${total_value:,.2f} | 现金: ${usd:,.2f}")

            # 2. 风控检查
            if not self.risk.check(total_value, positions):
                logger.warning("触发风控拦截")
                return

            # 3. 执行策略逻辑
            self.rebalance(prices, balance, total_value)

        except Exception as e:
            logger.error(f"策略循环错误: {e}", exc_info=True)

    def run(self):
        logger.info("均线交叉策略启动...")
        while True:
            self.step()
            time.sleep(Config.INTERVAL)