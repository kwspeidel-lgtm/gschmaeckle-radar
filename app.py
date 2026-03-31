from flask import Flask, render_template_string, make_response
import yfinance as yf
import time

app = Flask(__name__)

# =========================
# CACHE
# =========================
CACHE = {}
CACHE_TIME = 30

def get_data(sym, period="5d", interval="1d"):
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
        if v > 10000:
            return "{:,}".format(v)
        return str(v)
    except:
        return ""

# =========================
# TICKER
# =========================
TICKERS = {
    "DAX": "^GDAXI",
    "SP500": "^GSPC",
    "Gold": "GC=F",
    "Silber": "SI=F",
    "Bitcoin": "BTC-USD"
}

# =========================
# MARKTDATEN
# =========================
def get_market_data():
    results = []

    for name, sym in TICKERS.items():
        h = get_data(sym, "5d")
        if h is None or len(h) < 2:
            continue

        try:
            p = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            chg = ((p - prev)/prev)*100

            if chg > 1:
                al = "success"; interp = "bullisch"
            elif chg < -1:
                al = "danger"; interp = "bärisch"
            else:
                al = "warning"; interp = "neutral"

            results.append({
                "name": name,
                "p": f"{p:.2f}",
                "chg": f"{chg:+.2f}%",
                "al": al,
                "interpretation": interp
            })

        except:
            continue

    # =========================
    # GOLD/SILBER
    # =========================
    try:
        g = get_data("GC=F", "2d")
        s = get_data("SI=F", "2d")

        ratio = g['Close'].iloc[-1] / s['Close'].iloc[-1]
        ratio_prev = g['Close'].iloc[-2] / s['Close'].iloc[-2]
        ratio_chg = ((ratio - ratio_prev)/ratio_prev)*100
    except:
        ratio = 0
        ratio_chg = 0

    # =========================
    # 🔥 ÖL PRO (WTI + BRENT)
    # =========================
    def oil_block(symbol):
        try:
            d = get_data(symbol, "2d", "1h")  # Intraday!
            if d is None or len(d) < 2:
                return None

            close_now = d['Close'].iloc[-1]
            close_prev = d['Close'].iloc[-2]
            chg = ((close_now - close_prev)/close_prev)*100

            vol_now = d['Volume'].iloc[-1]
            vol_prev = d['Volume'].iloc[-2]

            if vol_now > vol_prev:
                vol_trend = "Volumen steigend"
            elif vol_now < vol_prev:
                vol_trend = "Volumen fallend"
            else:
                vol_trend = "Volumen gleich"

            return {
                "price": "{:,.2f}".format(close_now),
                "chg": f"{chg:+.2f}%",
                "vol_now": fmt_vol(vol_now),
                "vol_prev": fmt_vol(vol_prev),
                "vol_trend": vol_trend
            }
        except:
            return None

    wti = oil_block("CL=F")
    brent = oil_block("BZ=F")

    return results, ratio, ratio_chg, wti, brent

# =========================
# ANOMALIE CHECK
# =========================
def anomaly_check(results, ratio_chg, wti):
    score = 0
    reasons = []

    # Öl Bewegung + Volumen
    try:
        oil_move = float(wti["chg"].replace("%", ""))
        if abs(oil_move) > 1:
            score += 1
            reasons.append("Öl Bewegung")

        if "steigend" in wti["vol_trend"]:
            score += 1
            reasons.append("Öl Volumen")
    except:
        pass

    # Ratio
    if abs(ratio_chg) > 0.5:
        score += 1
        reasons.append("Gold/Silber")

    # große Moves
    for a in results:
        try:
            chg = float(a["chg"].replace("%", ""))
            if abs(chg) > 1.5:
                score += 1
                reasons.append(a["name"])
        except:
            pass

    if score >= 4:
        status = "🔴 Unregelmäßig"
    elif score >= 2:
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
.card{background:#161616;padding:10px;margin:5px;border-radius:10px;border:2px solid #333;}
</style>
</head>
<body>

<h3>Gschmäckle Radar PRO</h3>

<h4>Status: {{status}}</h4>

<div class="card">
{% for r in reasons %}
- {{r}}<br>
{% endfor %}
</div>

<h4>Gold/Silber: {{ratio|round(2)}} ({{ratio_chg|round(2)}}%)</h4>

{% for a in assets %}
<div class="card">
<b>{{a.name}}</b> {{a.chg}}<br>
Preis: {{a.p}}<br>
</div>
{% endfor %}

<div class="card">
<h4>WTI Öl</h4>
Preis: {{wti.price}}<br>
{{wti.chg}}<br>
Vol: {{wti.vol_now}} vs {{wti.vol_prev}}<br>
{{wti.vol_trend}}
</div>

<div class="card">
<h4>Brent Öl</h4>
Preis: {{brent.price}}<br>
{{brent.chg}}<br>
Vol: {{brent.vol_now}} vs {{brent.vol_prev}}<br>
{{brent.vol_trend}}
</div>

</body>
</html>
"""

# =========================
# ROUTE
# =========================
@app.route("/")
def home():
    assets, ratio, ratio_chg, wti, brent = get_market_data()
    status, reasons = anomaly_check(assets, ratio_chg, wti)

    return render_template_string(
        HTML,
        assets=assets,
        ratio=ratio,
        ratio_chg=ratio_chg,
        wti=wti,
        brent=brent,
        status=status,
        reasons=reasons
    )

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(debug=True)
