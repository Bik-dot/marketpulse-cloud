import requests
import time
import yfinance as yf
import traceback
import os
from datetime import datetime, timedelta
import pandas as pd

# --- ENV VARIABLES ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# -------- TELEGRAM ALERT --------
def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)


# -------- WATCHLIST --------
stocks = ["RELIANCE.NS", "HDFCBANK.NS", "SBIN.NS"]

# -------- DUPLICATE ALERT MEMORY --------
alert_cooldown_minutes = 45
last_alert_time = {}

# -------- SIGNAL MEMORY FILE --------
LOG_FILE = "signal_memory.csv"

if not os.path.exists(LOG_FILE):
    df = pd.DataFrame(columns=["time","stock","change","volume","trend"])
    df.to_csv(LOG_FILE, index=False)


# -------- SAFE PRICE EXTRACTOR --------
def get_price(value):
    try:
        if hasattr(value, "values"):
            value = value.values[0]
        return float(value)
    except:
        return None


# -------- NSE MARKET HOURS FILTER --------
def is_market_open():
    now = datetime.now()

    # weekday check
    if now.weekday() >= 5:
        return False

    start = now.replace(hour=9, minute=15, second=0)
    end = now.replace(hour=15, minute=30, second=0)

    return start <= now <= end


# -------- DUPLICATE CHECK --------
def can_send_alert(stock):
    now = datetime.now()

    if stock in last_alert_time:
        last_time = last_alert_time[stock]
        if now - last_time < timedelta(minutes=alert_cooldown_minutes):
            return False

    last_alert_time[stock] = now
    return True


# -------- TREND DETECTOR --------
def get_trend(data):
    try:
        ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
        ema50 = data["Close"].ewm(span=50).mean().iloc[-1]

        price = get_price(data["Close"].iloc[-1])

        if price > ema20 > ema50:
            return "UPTREND"
        elif price < ema20 < ema50:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    except:
        return "UNKNOWN"


# -------- SIGNAL MEMORY SAVE --------
def save_signal(stock, change, volume, trend):
    row = {
        "time": datetime.now(),
        "stock": stock,
        "change": change,
        "volume": volume,
        "trend": trend
    }
    pd.DataFrame([row]).to_csv(LOG_FILE, mode='a', header=False, index=False)


# -------- MARKET CHECK FUNCTION --------
def check_market():
    movers = []

    # Market hours check
    if not is_market_open():
        print("Market closed. Scanner idle.")
        return movers

    for s in stocks:
        try:
            print(f"Checking {s}")

            data = yf.download(
                s,
                period="1d",
                interval="5m",
                progress=False,
                threads=False
            )

            if data is None or data.empty or len(data) < 10:
                continue

            last = get_price(data["Close"].iloc[-1])
            prev = get_price(data["Close"].iloc[-2])

            volume = get_price(data["Volume"].iloc[-1])
            avg_volume = data["Volume"].rolling(10).mean().iloc[-1]

            if last is None or prev is None or prev == 0:
                continue

            change = ((last - prev) / prev) * 100

            # -------- SIGNAL FILTERS --------

            # 1) price move filter
            if abs(change) < 0.7:
                continue

            # 2) volume confirmation
            if volume < avg_volume:
                print(f"{s} weak volume")
                continue

            # 3) trend confirmation
            trend = get_trend(data)

            if trend == "SIDEWAYS":
                print(f"{s} sideways skip")
                continue

            # 4) duplicate blocker
            if not can_send_alert(s):
                print(f"{s} cooldown active")
                continue

            # Save signal for learning
            save_signal(s, change, volume, trend)

            movers.append(f"{s} {round(change,2)}% | Vol↑ | {trend}")

        except Exception as e:
            print(f"Error in {s}:", e)
            traceback.print_exc()

    return movers


# -------- MAIN LOOP --------
def run_scanner():
    print("MarketPulse Intelligent Scanner LIVE")

    send_alert("MarketPulse Intelligent Scanner ACTIVE")

    while True:
        try:
            movers = check_market()

            if movers:
                msg = "High-Quality Signals:\n" + "\n".join(movers)
                print(msg)
                send_alert(msg)
            else:
                print("No strong signals.")

            time.sleep(180)

        except Exception as e:
            print("Main loop error:", e)
            traceback.print_exc()
            time.sleep(60)


# -------- START --------
if __name__ == "__main__":
    run_scanner()
