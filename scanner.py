import requests
import yfinance as yf
import pandas as pd
import numpy as np
import time

# TELEGRAM
BOT_TOKEN = "8310483280:AAEfkiBbZ_fk4Hg8eqma37ts2rc3D0Wy-EA"
CHAT_ID = "1368954408"

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})


# NSE SECTOR WATCHLIST (Institutional Core Universe)
sectors = {
    "BANKING": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"],
    "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
    "ENERGY": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS"],
    "PHARMA": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
    "AUTO": ["TATAMOTORS.NS", "MARUTI.NS", "M&M.NS"],
    "PSU": ["SBIN.NS", "NTPC.NS", "COALINDIA.NS", "POWERGRID.NS"]
}

startup_flag = False

if not startup_flag:
    send_alert("MarketPulse Institutional Scanner Running")
    startup_flag = True
def get_signal(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="1m")

        price = data["Close"].iloc[-1]
        ema = data["Close"].ewm(span=20).mean().iloc[-1]

        volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        atr = (data["High"] - data["Low"]).rolling(14).mean().iloc[-1]

        breakout = price > data["High"].rolling(10).max().iloc[-1]
        trend = price > ema
        volume_spike = volume > avg_volume * 1.5
        volatility = atr > atr.mean()

        score = sum([breakout, trend, volume_spike, volatility])

        return score

    except:
        return 0


while True:
    sector_scores = {}

    # 1-MINUTE MARKET SCAN
    for sector, stocks in sectors.items():
        total_score = 0

        for stock in stocks:
            total_score += get_signal(stock)

        sector_scores[sector] = total_score

    # FIND HOT SECTOR
    best_sector = max(sector_scores, key=sector_scores.get)

    # ALERT ONLY IF STRONG
    if sector_scores[best_sector] > 6:
        message = f"""
SECTOR ACTIVE: {best_sector}

Institutional momentum detected.
Volume + Trend + Breakout alignment.
"""
        send_alert(message)

    # Hybrid mode:
    # scan every 1 min
    time.sleep(60)

