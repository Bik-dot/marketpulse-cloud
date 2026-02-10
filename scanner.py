import requests
import yfinance as yf
import pandas as pd
import numpy as np
import time

# TELEGRAM SETTINGS
BOT_TOKEN = "8310483280:AAEfkiBbZ_fk4Hg8eqma37ts2rc3D0Wy-EA"
CHAT_ID = "1368954408"

def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass


# SECTOR STOCK UNIVERSE (LIGHTWEIGHT FOR CLOUD)
sectors = {
    "BANKING": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
    "IT": ["TCS.NS", "INFY.NS"],
    "ENERGY": ["RELIANCE.NS", "ONGC.NS"],
    "PHARMA": ["SUNPHARMA.NS", "DRREDDY.NS"],
    "AUTO": ["TATAMOTORS.NS", "M&M.NS"],
    "PSU": ["NTPC.NS", "COALINDIA.NS"]
}


def get_signal(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="5m")

        if data.empty:
            return 0

        price = data["Close"].iloc[-1]
        ema = data["Close"].ewm(span=20).mean().iloc[-1]

        volume = data["Volume"].iloc[-1]
        avg_volume = data["Volume"].rolling(20).mean().iloc[-1]

        breakout = price > data["High"].rolling(10).max().iloc[-1]
        trend = price > ema
        volume_spike = volume > avg_volume * 1.5

        score = sum([breakout, trend, volume_spike])
        return score

    except:
        return 0


# MAIN LOOP (STABLE CLOUD MODE)
while True:
    try:
        sector_scores = {}

        for sector, stocks in sectors.items():
            total_score = 0

            for stock in stocks:
                total_score += get_signal(stock)

            sector_scores[sector] = total_score

        best_sector = max(sector_scores, key=sector_scores.get)

        # Only alert on strong institutional movement
        if sector_scores[best_sector] >= 5:
            message = f"""
SECTOR MOMENTUM DETECTED: {best_sector}

Institutional activity:
Trend + Volume + Breakout alignment
"""
            send_alert(message)

        # Run every 5 minutes (cloud safe)
        time.sleep(300)

    except:
        time.sleep(120)

