# config.py
"""
(配置层)
职责：将硬编码的参数和环境变量加载分离出来，作为全局配置中心。


来源参考： (.env),  (SYMBOLS list)
"""
import os
from dotenv import load_dotenv

# 加载 .env
load_dotenv()

class Config:
    # API 配置
    ROOSTOO_API_KEY = os.getenv("ROOSTOO_API_KEY")
    ROOSTOO_API_SECRET = os.getenv("ROOSTOO_API_SECRET")
    HORUS_API_KEY = os.getenv("HORUS_API_KEY")
    BASE_URL = "https://mock-api.roostoo.com"#**
    HORUS_BASE_URL = "https://api-horus.com"#**

    # 运行模式
    DRY_RUN = os.getenv("DRY_RUN", "False").lower() == "true"
    
    # 策略参数
    BASE_PER_PERCENT = 2000  # 每涨 1% 分配 $2,000
    INTERVAL = 3600          # 调仓间隔 (秒)
    
    # 交易对列表
    SYMBOLS = [
        "BTC/USD", "ETH/USD", "XRP/USD", "BNB/USD", "SOL/USD", "DOGE/USD",
        "TRX/USD", "ADA/USD", "XLM/USD", "WBTC/USD", "SUI/USD", "HBAR/USD",
        "LINK/USD", "BCH/USD", "WBETH/USD", "UNI/USD", "AVAX/USD", "SHIB/USD",
        "TON/USD", "LTC/USD", "DOT/USD", "PEPE/USD", "AAVE/USD", "ONDO/USD",
        "TAO/USD", "WLD/USD", "APT/USD", "NEAR/USD", "ARB/USD", "ICP/USD",
        "ETC/USD", "FIL/USD", "TRUMP/USD", "OP/USD", "ALGO/USD", "POL/USD",
        "BONK/USD", "ENA/USD", "ENS/USD", "VET/USD", "SEI/USD", "RENDER/USD",
        "FET/USD", "ATOM/USD", "VIRTUAL/USD", "SKY/USD", "BNSOL/USD", "RAY/USD",
        "TIA/USD", "JTO/USD", "JUP/USD", "QNT/USD", "FORM/USD", "INJ/USD",
        "STX/USD"
    ]