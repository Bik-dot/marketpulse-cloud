import requests
import time
import yfinance as yf
import traceback
import os
from datetime import datetime, timedelta
import pandas as pd
import pytz

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET")
UPSTOX_MODE = os.getenv("UPSTOX_MODE")
UPSTOX_PAPER = os.getenv("UPSTOX_PAPER")

IST = pytz.timezone('Asia/Kolkata')

# ================= TELEGRAM =================
def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass

# ================= WATCHLIST =================
stocks = [
"RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","TCS.NS",
"ITC.NS","LT.NS","AXISBANK.NS","KOTAKBANK.NS","HINDUNILVR.NS",
"SBIN.NS","BHARTIARTL.NS","BAJFINANCE.NS","BAJAJFINSV.NS",
"ASIANPAINT.NS","MARUTI.NS","SUNPHARMA.NS","TITAN.NS",
"ULTRACEMCO.NS","WIPRO.NS","ONGC.NS","NTPC.NS","POWERGRID.NS",
"ADANIENT.NS","ADANIPORTS.NS","TATASTEEL.NS","JSWSTEEL.NS",
"HCLTECH.NS","TECHM.NS","COALINDIA.NS","BPCL.NS","IOC.NS",
"DRREDDY.NS","EICHERMOT.NS","GRASIM.NS","HEROMOTOCO.NS",
"HINDALCO.NS","INDUSINDBK.NS","NESTLEIND.NS","SBILIFE.NS",
"SHREECEM.NS","UPL.NS","DIVISLAB.NS","CIPLA.NS","BRITANNIA.NS"
]

# ================= RISK MEMORY =================
alert_cooldown_minutes = 45
last_alert_time = {}
LOG_FILE = "signal_memory.csv"

if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["time","stock","change","volume","trend","confidence"]).to_csv(LOG_FILE, index=False)

# ================= HELPERS =================
def get_price(value):
    try:
        if hasattr(value, "values"):
            value = value.values[0]
        return float(value)
    except:
        return None

def is_market_open():
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    start = now.replace(hour=9, minute=15, second=0)
    end = now.replace(hour=15, minute=30, second=0)
    return start <= now <= end

def can_send_alert(stock):
    now = datetime.now(IST)
    if stock in last_alert_time:
        if now - last_alert_time[stock] < timedelta(minutes=alert_cooldown_minutes):
            return False
    last_alert_time[stock] = now
    return True

# ================= TREND =================
def get_trend(data):
    try:
        ema20 = get_price(data["Close"].ewm(span=20).mean().iloc[-1])
        ema50 = get_price(data["Close"].ewm(span=50).mean().iloc[-1])
        price = get_price(data["Close"].iloc[-1])
        if price > ema20 and ema20 > ema50:
            return "UPTREND"
        elif price < ema20 and ema20 < ema50:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    except:
        return "UNKNOWN"

# ================= CONFIDENCE =================
def confidence_score(change, volume, avg_volume, trend):
    score = 0
    if abs(change) > 1:
        score += 40
    elif abs(change) > 0.7:
        score += 30
    elif abs(change) > 0.4:
        score += 20
    if volume > avg_volume:
        score += 25
    if trend in ["UPTREND","DOWNTREND"]:
        score += 30
    return score

# ================= EXECUTION ENGINE =================
def execute_paper_trade(stock, price, confidence, trend):
    capital = 12000

    if confidence >= 80:
        allocation = 4000
        risk = 240
        grade = "A"
    elif confidence >= 65:
        allocation = 2500
        risk = 180
        grade = "B"
    else:
        allocation = 1500
        risk = 120
        grade = "C"

    stop_loss = round(price * 0.99, 2)

    msg = f"""
TRADE SIGNAL (PAPER MODE)

Stock: {stock}
Trend: {trend}
Confidence: {confidence}
Grade: {grade}

Capital: ₹{allocation}
Risk: ₹{risk}
Stop Loss: {stop_loss}
"""

    print(msg)
    send_alert(msg)

# ================= SCANNER =================
def check_market():
    if not is_market_open():
        print("Market closed.")
        return

    for s in stocks:
        try:
            data = yf.download(s, period="2d", interval="5m", progress=False, threads=False)
            if data is not None and len(data) > 2:
                data = data.iloc[:-1]

            if data is None or data.empty or len(data) < 15:
                continue

            last = get_price(data["Close"].iloc[-1])
            prev = get_price(data["Close"].iloc[-2])

            volume = get_price(data["Volume"].iloc[-1])
            avg_volume = get_price(data["Volume"].rolling(10).mean().iloc[-1])

            change = ((last - prev) / prev) * 100

            if abs(change) < 0.4:
                continue

            trend = get_trend(data)
            confidence = confidence_score(change, volume, avg_volume, trend)

            if confidence < 45:
                continue

            if not can_send_alert(s):
                continue

            execute_paper_trade(s, last, confidence, trend)

        except Exception as e:
            print("Error:", e)
            traceback.print_exc()

# ================= LOOP =================
def run():
    send_alert("MarketPulse Trading Engine Started (Paper Mode)")
    while True:
        check_market()
        time.sleep(180)

if __name__ == "__main__":
    run()
