from flask import Flask, render_template_string, make_response
import yfinance as yf
import time

app = Flask(__name__)

# =========================
# CACHE
# =========================
CACHE = {}
CACHE_TIME = 30

def get_data(sym, period="5d"):
    now = time.time()
    key = f"{sym}_{period}"

    if key in CACHE and now - CACHE[key]['time'] < CACHE_TIME:
        return CACHE[key]['data']

    try:
        data = yf.download(sym, period=period, progress=False)
        CACHE[key] = {"data": data, "time": now}
        return data
    except:
        return None

# =========================
# TICKER
# =========================
TICKERS = {
    "DAX": "^GDAXI",
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "Silber": "SI=F",
    "Öl": "CL=F",
    "Bitcoin": "BTC-USD",
    "EUR/USD": "EURUSD=X"
}

# =========================
# DATEN
# =========================
def get_market_data():
    results = []

    for name, sym in TICKERS.items():
        h = get_data(sym, "5d")
        if h is None or h.empty or len(h) < 2:
            continue

        try:
            p = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            chg = ((p - prev)/prev)*100

            is_fx = sym == "EURUSD=X"
            is_special = sym in ["CL=F", "BTC-USD"]

            # Preisformat
            if is_fx:
                price_str = f"{p:.4f}"
            elif is_special:
                price_str = "{:,.2f}".format(p)
            else:
                price_str = f"{p:.2f}"

            # Volumen
            rv_str = ""
            if is_special:
                try:
                    rv_str = "{:,}".format(int(h['Volume'].iloc[-1]))
                except:
                    rv_str = ""

            # Interpretation
            if chg > 1:
                al = "success"
                interp = "bullisch"
            elif chg < -1:
                al = "danger"
                interp = "bärisch"
            else:
                al = "warning"
                interp = "neutral"

            results.append({
                "name": name,
                "p": price_str,
                "chg": f"{chg:+.2f}%",
                "rv": rv_str,
                "al": al,
                "interpretation": interp
            })

        except:
            continue

    # Öl Volumen heute vs gestern
    try:
        oil = get_data("CL=F", "5d")
        v1 = int(oil['Volume'].iloc[-1])
        v2 = int(oil['Volume'].iloc[-2])

        if v1 > v2:
            oil_al = "success"
        elif v1 < v2:
            oil_al = "danger"
        else:
            oil_al = "warning"

        shortcut2 = {
            "today": "{:,}".format(v1),
            "yesterday": "{:,}".format(v2),
            "al": oil_al
        }
    except:
        shortcut2 = {"today": "", "yesterday": "", "al": "warning"}

    return results, shortcut2

# =========================
# HTML
# =========================
HTML = """
<html>
<head>
<meta charset="UTF-8">
<title>Radar</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:sans-serif;}
.card{background:#161616;padding:10px;margin:5px;border-radius:10px;}
.text-success{color:#39ff14;}
.text-warning{color:#ffcc00;}
.text-danger{color:#ff3131;}
</style>
</head>
<body>

<h3>Live Radar</h3>

{% for a in assets %}
<div class="card border-{{a.al}}">
<b>{{a.name}}</b> {{a.chg}}<br>
Preis: {{a.p}}<br>
Vol: {{a.rv}}<br>
{{a.interpretation}}
</div>
{% endfor %}

<div class="card border-{{shortcut2.al}}">
<b>Öl Volumen</b><br>
Heute: {{shortcut2.today}}<br>
Gestern: {{shortcut2.yesterday}}
</div>

</body>
</html>
"""

# =========================
# ROUTE
# =========================
@app.route("/")
def home():
    assets, shortcut2 = get_market_data()

    response = make_response(
        render_template_string(HTML, assets=assets, shortcut2=shortcut2)
    )

    # 🔄 Auto Refresh alle 30 Sekunden
    response.headers["Refresh"] = "30"

    return response

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
