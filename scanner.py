import requests
import time
import yfinance as yf
import traceback
import os

# --- ENV VARIABLES (SAFE FOR RAILWAY) ---
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

            last = float(data["Close"].iloc[-1])
            prev = float(data["Close"].iloc[-2])

            if prev == 0:
                continue

            change = ((last - prev) / prev) * 100

            if abs(change) > 0.7:
                movers.append(f"{s} move {round(change,2)}%")

        except Exception as e:
            print(f"Error in {s}:", e)
            traceback.print_exc()
            continue

    return movers


# -------- MAIN LOOP --------
def run_scanner():
    print("Scanner started successfully...")

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


    except Exception as e:
        time.sleep(60)

