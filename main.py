# main.py
"""(入口)
职责：程序的启动点。负责实例化服务，获取初始状态，并启动 Bot。


来源参考： (Original main block)
"""

import time
from loguru import logger
from config import Config
from exchange_service import ExchangeService
from momentum_bot import MomentumBot

if __name__ == "__main__":
    # 配置日志
    logger.add("champion_bot.log", rotation="10 MB", level="INFO")
    
    # 初始化服务层
    service = ExchangeService()
    
    # 获取初始资金
    initial_balance = service.get_flattened_balance()
    initial_cash = initial_balance.get("USD", 0)
    logger.info(f"初始资金: ${initial_cash:,.2f}")
    
    # 启动策略
    # 稍微延迟确保连接建立
    time.sleep(1)
    
    bot = MomentumBot(service, initial_cash)
    bot.run()