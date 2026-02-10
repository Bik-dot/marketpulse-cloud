import requests
import time
import yfinance as yf

BOT_TOKEN = "8310483280:AAEfkiBbZ_fk4Hg8eqma37ts2rc3D0Wy-EA"
CHAT_ID = "1368954408"

def send_alert(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass


# very small stable watchlist
stocks = ["RELIANCE.NS", "HDFCBANK.NS", "SBIN.NS"]

def check_market():
    movers = []

    for s in stocks:
        try:
            data = yf.download(s, period="1d", interval="5m")

            if data.empty:
                continue

            last = data["Close"].iloc[-1]
            prev = data["Close"].iloc[-2]

            change = ((last - prev) / prev) * 100

            if abs(change) > 0.7:
                movers.append(f"{s} move {round(change,2)}%")

        except:
            continue

    return movers


while True:
    try:
        movers = check_market()

        if movers:
            msg = "Market Movers:\n" + "\n".join(movers)
            send_alert(msg)

        # keep service alive
        time.sleep(180)

    except Exception as e:
        time.sleep(60)

