import requests
import time
import yfinance as yf
import traceback
import os
from datetime import datetime
import pandas as pd
import pytz
import sqlite3
from flask import Flask, jsonify, request
from threading import Thread

app = Flask(__name__)

# ================= MEMORY STORE =================
live_signals = []

# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

IST = pytz.timezone('Asia/Kolkata')

# ================= DATABASE =================
DB_FILE = "signals.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            stock TEXT,
            change REAL,
            trend TEXT,
            confidence INTEGER
        )
    """)
    conn.commit()
    conn.close()

def save_signal(signal):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO signals (time, stock, change, trend, confidence)
        VALUES (?, ?, ?, ?, ?)
    """, (
        signal["time"],
        signal["stock"],
        signal["change"],
        signal["trend"],
        signal["confidence"]
    ))
    conn.commit()
    conn.close()

# ================= TELEGRAM =================
def send_alert(message):
    try:
        if BOT_TOKEN and CHAT_ID:
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

    if volume and avg_volume and volume > avg_volume:
        score += 25

    if trend in ["UPTREND","DOWNTREND"]:
        score += 30

    return score

# ================= SCANNER =================
def run_scanner():
    global live_signals

    while True:
        try:
            if not is_market_open():
                time.sleep(60)
                continue

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

                    if not last or not prev:
                        continue

                    change = ((last - prev) / prev) * 100

                    if abs(change) < 0.4:
                        continue

                    trend = get_trend(data)
                    confidence = confidence_score(change, volume, avg_volume, trend)

                    if confidence < 45:
                        continue

                    signal = {
                        "time": str(datetime.now(IST)),
                        "stock": s,
                        "change": round(change,2),
                        "trend": trend,
                        "confidence": confidence
                    }

                    live_signals.insert(0, signal)
                    live_signals = live_signals[:50]

                    save_signal(signal)
                    send_alert(f"Signal: {s} | Conf:{confidence} | {trend}")

                except Exception as e:
                    print("Scanner error:", e)
                    traceback.print_exc()

            time.sleep(180)

        except Exception as e:
            print("Main loop error:", e)
            traceback.print_exc()
            time.sleep(60)

# ================= API =================
@app.route("/signals")
def signals():
    return jsonify(live_signals)

@app.route("/history")
def history():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT time, stock, change, trend, confidence FROM signals ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        history_data = []
        for r in rows:
            history_data.append({
                "time": r[0],
                "stock": r[1],
                "change": r[2],
                "trend": r[3],
                "confidence": r[4]
            })

        return jsonify(history_data)
    except Exception as e:
        return {"error": str(e)}

@app.route("/status")
def status():
    return {"status":"running"}

@app.route("/system-log", methods=["POST"])
def receive_system_log():
    data = request.json
    print("SYSTEM LOG RECEIVED:", data)
    return {"status": "ok"}, 200

# ================= START =================
if __name__ == "__main__":
    init_db()
    Thread(target=run_scanner).start()
    app.run(host="0.0.0.0", port=8080)
