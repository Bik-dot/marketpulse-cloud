import requests
import time
import yfinance as yf
import traceback
import os
from datetime import datetime, timedelta
import pandas as pd
import pytz

IST = pytz.timezone('Asia/Kolkata')

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

stocks = ["RELIANCE.NS", "HDFCBANK.NS", "SBIN.NS"]

alert_cooldown_minutes = 45
last_alert_time = {}

LOG_FILE = "signal_memory.csv"

if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=["time","stock","change","volume","trend","confidence"]).to_csv(LOG_FILE, index=False)


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


# ---------- FIXED TREND FUNCTION ----------
def get_trend(data):
    try:
        ema20_series = data["Close"].ewm(span=20).mean()
        ema50_series = data["Close"].ewm(span=50).mean()

        ema20 = get_price(ema20_series.iloc[-1])
        ema50 = get_price(ema50_series.iloc[-1])
        price = get_price(data["Close"].iloc[-1])

        if ema20 is None or ema50 is None or price is None:
            return "UNKNOWN"

        if price > ema20 and ema20 > ema50:
            return "UPTREND"
        elif price < ema20 and ema20 < ema50:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"

    except:
        return "UNKNOWN"


def confidence_score(change, volume, avg_volume, trend):
    score = 0

    if abs(change) > 1:
        score += 40
    elif abs(change) > 0.7:
        score += 25

    if volume > avg_volume:
        score += 30

    if trend in ["UPTREND", "DOWNTREND"]:
        score += 30

    return score


def save_signal(stock, change, volume, trend, confidence):
    row = {
        "time": datetime.now(IST),
        "stock": stock,
        "change": change,
        "volume": volume,
        "trend": trend,
        "confidence": confidence
    }
    pd.DataFrame([row]).to_csv(LOG_FILE, mode='a', header=False, index=False)


def check_market():
    movers = []

    if not is_market_open():
        print("Market closed (IST).")
        return movers

    for s in stocks:
        try:
            print(f"Checking {s}")

            data = yf.download(s, period="1d", interval="5m", progress=False, threads=False)

            if data is None or data.empty or len(data) < 10:
                continue

            last = get_price(data["Close"].iloc[-1])
            prev = get_price(data["Close"].iloc[-2])

            volume = get_price(data["Volume"].iloc[-1])
            avg_volume = get_price(data["Volume"].rolling(10).mean().iloc[-1])

            if last is None or prev is None or prev == 0:
                continue

            change = ((last - prev) / prev) * 100

            trend = get_trend(data)

            confidence = confidence_score(change, volume, avg_volume, trend)

            if confidence < 60:
                continue

            if not can_send_alert(s):
                continue

            save_signal(s, change, volume, trend, confidence)

            movers.append(f"{s} {round(change,2)}% | Conf:{confidence} | {trend}")

        except Exception as e:
            print(f"Error in {s}:", e)
            traceback.print_exc()

    return movers


def run_scanner():
    print("MarketPulse PRO Scanner LIVE")

    send_alert("MarketPulse PRO Scanner ACTIVE")

    while True:
        try:
            movers = check_market()

            if movers:
                msg = "PRO Signals:\n" + "\n".join(movers)
                print(msg)
                send_alert(msg)
            else:
                print("No institutional signals.")

            time.sleep(180)

        except Exception as e:
            print("Main loop error:", e)
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    run_scanner()
