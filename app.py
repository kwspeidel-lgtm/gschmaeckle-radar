from flask import Flask, render_template_string
import yfinance as yf
import time

app = Flask(__name__)

# =========================
# CACHE
# =========================
CACHE = {}
CACHE_TIME = 30

def get_data(sym, period="5d", interval="1h"):
    now = time.time()
    key = f"{sym}_{period}_{interval}"

    if key in CACHE and now - CACHE[key]['time'] < CACHE_TIME:
        return CACHE[key]['data']

    try:
        data = yf.download(sym, period=period, interval=interval, progress=False)
        if data.empty:
            return None
        CACHE[key] = {"data": data, "time": now}
        return data
    except:
        return None

# =========================
# FORMAT
# =========================
def fmt_vol(v):
    try:
        v = int(v)
        return "{:,}".format(v).replace(",", ".")
    except:
        return ""

# =========================
# TICKER
# =========================
TICKERS = {
    "DAX": "^GDAXI",
    "SP500": "^GSPC",
    "Gold": "GC=F",
    "Silber": "SI=F"
}

# =========================
# MARKTDATEN
# =========================
def get_market_data():
    results = []

    for name, sym in TICKERS.items():
        h = get_data(sym, "5d", "1d")
        if h is None or len(h) < 3:
            continue

        try:
            p = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            prev2 = h['Close'].iloc[-3]

            chg = ((p - prev)/prev)*100
            chg_prev = ((prev - prev2)/prev2)*100

            results.append({
                "name": name,
                "p": f"{p:.2f}",
                "chg": f"{chg:+.2f}%",
                "chg_raw": chg,
                "chg_prev": chg_prev
            })

        except:
            continue

    # =========================
    # GOLD/SILBER
    # =========================
    try:
        g = get_data("GC=F", "2d", "1d")
        s = get_data("SI=F", "2d", "1d")

        ratio = g['Close'].iloc[-1] / s['Close'].iloc[-1]
        ratio_prev = g['Close'].iloc[-2] / s['Close'].iloc[-2]
        ratio_chg = ((ratio - ratio_prev)/ratio_prev)*100
    except:
        ratio = 0
        ratio_chg = 0

    # =========================
    # ÖL
    # =========================
    def oil_block(symbol):
        try:
            d = get_data(symbol, "2d", "1h")
            if d is None or len(d) < 25:
                return None

            close_now = d['Close'].iloc[-1]
            close_prev = d['Close'].iloc[-2]
            chg = ((close_now - close_prev)/close_prev)*100

            vol_now = d['Volume'].iloc[-1]
            vol_yest = d['Volume'].iloc[-25]

            return {
                "price": "{:,.2f}".format(close_now),
                "chg": f"{chg:+.2f}%",
                "chg_raw": chg,
                "vol_now": fmt_vol(vol_now),
                "vol_prev": fmt_vol(vol_yest),
                "vol_trend": "steigend" if vol_now > vol_yest else "fallend"
            }
        except:
            return None

    wti = oil_block("CL=F")
    brent = oil_block("BZ=F")

    return results, ratio, ratio_chg, wti, brent

# =========================
# LEVEL 3 ANOMALIE
# =========================
def anomaly_check(results, ratio_chg, wti):
    score = 0
    reasons = []

    # Öl Bewegung
    try:
        if abs(wti["chg_raw"]) > 1:
            score += 1
            reasons.append("Öl Bewegung")

        if wti["vol_trend"] == "steigend":
            score += 1
            reasons.append("Öl Volumen")
    except:
        pass

    # Ratio
    if abs(ratio_chg) > 0.5:
        score += 1
        reasons.append("Gold/Silber")

    # Momentum Spike
    for a in results:
        try:
            if abs(a["chg_raw"]) > abs(a["chg_prev"]) * 1.5:
                score += 1
                reasons.append(f"Momentum {a['name']}")
        except:
            pass

    # 🔴 Divergenz (KEY SIGNAL)
    try:
        dax = next(x for x in results if x["name"] == "DAX")
        gold = next(x for x in results if x["name"] == "Gold")

        if dax["chg_raw"] > 0 and gold["chg_raw"] > 0:
            score += 1
            reasons.append("Divergenz Aktien/Gold")

        if wti["chg_raw"] > 0 and dax["chg_raw"] < 0:
            score += 2
            reasons.append("Öl vs Aktien Divergenz")
    except:
        pass

    # Bewertung
    if score >= 5:
        status = "🔴 Unregelmäßig"
    elif score >= 3:
        status = "🟡 Auffällig"
    else:
        status = "🟢 Normal"

    return status, reasons

# =========================
# HTML
# =========================
HTML = """
<html>
<head>
<meta charset="UTF-8">
<style>
body{background:#0a0a0a;color:#fff;font-family:sans-serif;}
.card{background:#161616;padding:10px;margin:5px;border-radius:10px;}
</style>
</head>
<body>

<h3>Gschmäckle Radar PRO - Level 3</h3>

<h4>Status: {{status}}</h4>

<div class="card">
{% for r in reasons
