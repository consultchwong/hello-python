from workers import handler, Response
import json
import yfinance as yf
import talib
import pandas as pd
from datetime import datetime, timedelta

@handler
async def on_fetch(request, env):
    # 1. 解析请求参数
    ticker = request.query.get("ticker", "AAPL").upper()
    period = request.query.get("period", "1mo")
    interval = request.query.get("interval", "1d")
    
    try:
        # 2. 获取历史数据
        stock = yf.Ticker(ticker)
        hist = stock.history(
            period=period,
            interval=interval,
            auto_adjust=True
        )
        
        # 3. 计算技术指标
        closes = hist["Close"].values
        hist["RSI"] = talib.RSI(closes, timeperiod=14)
        hist["MACD"], hist["MACD_Signal"], _ = talib.MACD(closes)
        hist["SMA_20"] = talib.SMA(closes, timeperiod=20)
        
        # 4. 格式化输出
        hist = hist[["Close", "RSI", "MACD", "MACD_Signal", "SMA_20"]]
        hist = hist.dropna()  # 清除空值
        data = {
            "ticker": ticker,
            "last_updated": datetime.utcnow().isoformat(),
            "indicators": json.loads(hist.tail(10).to_json(orient="records"))
        }
        
        return Response(json.dumps(data), headers={"Content-Type": "application/json"})
    
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500)
