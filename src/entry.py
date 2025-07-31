from workers import handler, Response
import json
import asyncio
import pyodide_js
from datetime import datetime, timedelta

# 计算技术指标的纯Python实现（避免TA-Lib依赖）
def calculate_indicators(df):
    """计算RSI、MACD和SMA20技术指标"""
    closes = df['Close']
    
    # 1. 计算RSI（相对强弱指数）
    delta = closes.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 2. 计算MACD（指数平滑移动平均线）
    ema12 = closes.ewm(span=12, adjust=False).mean()
    ema26 = closes.ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 3. 计算SMA20（20日简单移动平均）
    df['SMA_20'] = closes.rolling(window=20).mean()
    
    return df.dropna()

@handler
async def on_fetch(request, env):
    # 动态安装依赖（仅首次运行时）
    if not hasattr(env, 'deps_installed'):
        micropip = await pyodide_js.loadPackage('micropip')
        await micropip.install([
            'yfinance==0.2.18', 
            'pandas==2.0.3',
            'numpy==1.24.4'
        ])
        env.deps_installed = True
    
    # 1. 解析请求参数
    ticker = request.query.get("ticker", "AAPL").upper()
    period = request.query.get("period", "1mo")
    interval = request.query.get("interval", "1d")
    
    try:
        # 2. 动态导入安装的模块
        import yfinance as yf
        import pandas as pd

        # 3. 获取历史数据
        stock = yf.Ticker(ticker)
        hist = stock.history(
            period=period,
            interval=interval,
            auto_adjust=True
        )
        
        # 4. 计算技术指标
        hist = calculate_indicators(hist)
        
        # 5. 格式化输出
        data = {
            "ticker": ticker,
            "last_updated": datetime.utcnow().isoformat(),
            "indicators": json.loads(
                hist[["Close", "RSI", "MACD", "MACD_Signal", "SMA_20"]]
                .tail(10)
                .reset_index()
                .to_json(orient="records", date_format="iso")
            )
        }
        
        return Response(json.dumps(data), headers={"Content-Type": "application/json"})
    
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500)
