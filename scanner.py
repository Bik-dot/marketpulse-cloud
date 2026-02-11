import requests
import time
import yfinance as yf
import traceback
import os
from datetime import datetime, timedelta

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
last_alert_time = {}  # stock : datetime


# -------- SAFE PRICE EXTRACTOR --------
def get_price(value):
    try:
        if hasattr(value, "values"):
            value = value.values[0]
        return float(value)
    except:
        return None


# -------- DUPLICATE CHECK --------
def can_send_alert(stock):
    now = datetime.now()

    if stock in last_alert_time:
        last_time = last_alert_time[stock]
        if now - last_time < timedelta(minutes=alert_cooldown_minutes):
            return False

    last_alert_time[stock] = now
    return True


# -------- MARKET CHECK FUNCTION --------
def check_market():
    movers = []

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

            if data is None or data.empty or len(data) < 3:
                print(f"No data for {s}")
                continue

            last = get_price(data["Close"].iloc[-1])
            prev = get_price(data["Close"].iloc[-2])

            if last is None or prev is None or prev == 0:
                continue

            change = ((last - prev) / prev) * 100

            # SIGNAL CONDITION
            if abs(change) > 0.7:

                # DUPLICATE BLOCKER
                if can_send_alert(s):
                    movers.append(f"{s} move {round(change,2)}%")
                else:
                    print(f"{s} alert skipped (cooldown active)")

        except Exception as e:
            print(f"Error in {s}:", e)
            traceback.print_exc()

    return movers


# -------- MAIN LOOP --------
def run_scanner():
    print("Scanner started successfully...")

    send_alert("MarketPulse Scanner LIVE (duplicate blocker active)")

    while True:
        try:
            movers = check_market()

            if movers:
                msg = "Market Movers:\n" + "\n".join(movers)
                print(msg)
                send_alert(msg)
            else:
                print("No movers found.")

            time.sleep(180)

        except Exception as e:
            print("Main loop error:", e)
            traceback.print_exc()
            time.sleep(60)


# -------- START --------
if __name__ == "__main__":
    run_scanner()
