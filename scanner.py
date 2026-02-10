import requests
import yfinance as yf
import time

# TELEGRAM SETTINGS
BOT_TOKEN = "8310483280:AAEfkiBbZ_fk4Hg8eqma37ts2rc3D0Wy-EA"
CHAT_ID = "1368954408"

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

# NSE WATCHLIST (starter universe — later full India)
stocks = [
    "^NSEI", "^NSEBANK", "RELIANCE.NS", "TCS.NS", "INFY.NS",
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "ITC.NS"
]

send_alert("MarketPulse Cloud Scanner Started")

while True:
    movers = []

    for symbol in stocks:
        try:
            data = yf.download(symbol, period="1d", interval="5m")
            last_close = data["Close"].iloc[-1]
            prev_close = data["Close"].iloc[-2]

            change = ((last_close - prev_close) / prev_close) * 100

            if abs(change) > 0.5:
                movers.append(f"{symbol} move {round(change,2)}%")

        except:
            continue

    if movers:
        msg = "Top movers:\n" + "\n".join(movers)
        send_alert(msg)

    time.sleep(300)
