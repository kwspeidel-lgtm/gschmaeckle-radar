from flask import Flask, render_template_string, make_response
import yfinance as yf
import time

app = Flask(__name__)

# =========================
# CACHE
# =========================
CACHE = {}
CACHE_TIME = 30  # Sekunden

def get_data(sym, period="5d"):
    now = time.time()
    key = f"{sym}_{period}"

    if key in CACHE and now - CACHE[key]['time'] < CACHE_TIME:
        return CACHE[key]['data']

    try:
        data = yf.download(sym, period=period, progress=False)
        if data.empty:
            print(f"{sym} liefert keine Daten")
            return None
        CACHE[key] = {"data": data, "time": now}
        return data
    except Exception as e:
        print(f"Fehler bei {sym}: {e}")
        return None

# =========================
# TICKER
# =========================
TICKERS = {
    "DAX": "^GDAXI",
    "SP500": "^GSPC",
    "Gold": "GC=F",
    "Silber": "SI=F",
    "Oel": "CL=F",
    "Bitcoin": "BTC-USD",
    "EURUSD": "EURUSD=X"
}

# =========================
# MARKTDATEN
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

            # Volumen nur BTC
            rv_str = ""
            if sym == "BTC-USD":
                try:
                    rv_str = "{:,}".format(int(h['Volume'].iloc[-1]))
                except:
                    rv_str = ""

            # Interpretation
            if chg > 1:
                al = "success"; interp = "bullisch"
            elif chg < -1:
                al = "danger"; interp = "bärisch"
            else:
                al = "warning"; interp = "neutral"

            results.append({
                "name": name,
                "p": price_str,
                "chg": f"{chg:+.2f}%",
                "rv": rv_str,
                "al": al,
                "interpretation": interp
            })

        except Exception as e:
            print(f"Fehler beim Verarbeiten von {name}: {e}")
            continue

    # =========================
    # GOLD/SILBER RATIO
    # =========================
    try:
        g = get_data("GC=F", "2d")
        s = get_data("SI=F", "2d")
        if g is None or s is None:
            raise Exception("Gold oder Silber Daten fehlen")

        ratio = g['Close'].iloc[-1] / s['Close'].iloc[-1]
        ratio_prev = g['Close'].iloc[-2] / s['Close'].iloc[-2]
        ratio_chg = ((ratio - ratio_prev)/ratio_prev)*100

        if ratio_chg > 0.5:
            ratio_al = "success"
        elif ratio_chg < -0.5:
            ratio_al = "danger"
        else:
            ratio_al = "warning"

    except Exception as e:
        print(f"Fehler Gold/Silber Ratio: {e}")
        ratio = 0
        ratio_chg = 0
        ratio_al = "warning"

    # =========================
    # 🔥 ÖL PRO ANALYSE
    # =========================
    try:
        oil = get_data("CL=F", "5d")
        if oil is None or len(oil) < 2:
            raise Exception("Öl Daten fehlen")

        close_today = oil['Close'].iloc[-1]
        close_yest = oil['Close'].iloc[-2]

        high_today = oil['High'].iloc[-1]
        low_today = oil['Low'].iloc[-1]

        high_yest = oil['High'].iloc[-2]
        low_yest = oil['Low'].iloc[-2]

        # Preisveränderung
        oil_chg = ((close_today - close_yest)/close_yest)*100

        # Range heute vs gestern
        range_today = high_today - low_today
        range_yest = high_yest - low_yest

        range_str = f"{range_today:.2f}"
        range_delta = range_today - range_yest

        # Interpretation
        if oil_chg > 1 and range_today > range_yest:
            oil_text = "Bullisch + hohe Aktivität"
            oil_al = "success"
        elif oil_chg < -1 and range_today > range_yest:
            oil_text = "Bärisch + hohe Aktivität"
            oil_al = "danger"
        elif range_today < range_yest:
            oil_text = "Ruhiger Markt"
            oil_al = "warning"
        else:
            oil_text = "Neutral"
            oil_al = "warning"

        oil_data = {
            "price": "{:,.2f}".format(close_today),
            "chg": f"{oil_chg:+.2f}%",
            "range": range_str,
            "interpretation": oil_text,
            "al": oil_al
        }

    except Exception as e:
        print(f"Fehler Öl Analyse: {e}")
        oil_data = {
            "price": "",
            "chg": "",
            "range": "",
            "interpretation": "Fehler",
            "al": "danger"
        }

    return results, ratio, ratio_chg, ratio_al, oil_data

# =========================
# HTML
# =========================
HTML = """
<html>
<head>
<meta charset="UTF-8">
<title>Radar Pro</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:sans-serif;}
.card{background:#161616;padding:10px;margin:5px;border-radius:10px;border:2px solid #333;}
.text-success{color:#39ff14;}
.text-warning{color:#ffcc00;}
.text-danger{color:#ff3131;}
.border-success{border-color:#39ff14;}
.border-warning{border-color:#ffcc00;}
.border-danger{border-color:#ff3131;}
</style>
</head>
<body>

<h3>Gschmäckle Radar PRO</h3>

<h4>Gold/Silber Ratio: {{ratio|round(2)}} ({{ratio_chg|round(2)}}%)</h4>

{% for a in assets %}
<div class="card border-{{a.al}}">
<b>{{a.name}}</b> {{a.chg}}<br>
Preis: {{a.p}}<br>
{{a.interpretation}}
</div>
{% endfor %}

<div class="card border-{{oil.al}}">
<h4>Öl PRO Analyse</h4>
Preis: {{oil.price}}<br>
Veränderung: {{oil.chg}}<br>
Range: {{oil.range}}<br>
{{oil.interpretation}}
</div>

</body>
</html>
"""

# =========================
# ROUTE
# =========================
@app.route("/")
def home():
    assets, ratio, ratio_chg, ratio_al, oil = get_market_data()

    response = make_response(
        render_template_string(
            HTML,
            assets=assets,
            ratio=ratio,
            ratio_chg=ratio_chg,
            ratio_al=ratio_al,
            oil=oil
        )
    )

    response.headers["Refresh"] = "30"
    return response

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(debug=True)  # localhost:5000
