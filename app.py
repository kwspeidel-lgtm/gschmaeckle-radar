from flask import Flask, render_template_string, make_response
import yfinance as yf
import time

app = Flask(__name__)

# =========================
# CACHE
# =========================
CACHE = {}
CACHE_TIME = 30  # Sekunden

def get_data(sym, period="5d", interval="1h"):
    now = time.time()
    key = f"{sym}_{period}_{interval}"

    if key in CACHE and now - CACHE[key]['time'] < CACHE_TIME:
        return CACHE[key]['data']

    try:
        data = yf.download(sym, period=period, interval=interval, progress=False)
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
    "WTI": "CL=F",
    "Brent": "BZ=F",
    "Bitcoin": "BTC-USD",
    "EURUSD": "EURUSD=X"
}

# =========================
# FORMATIERUNG
# =========================
def format_de(zahl):
    f_str = f"{zahl:,.2f}"
    return f_str.replace(",", "X").replace(".", ",").replace("X", ".")

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

            # Preisformat
            is_fx = sym == "EURUSD=X"
            is_special = sym in ["CL=F", "BZ=F", "BTC-USD"]

            if is_fx:
                price_str = f"{p:.4f}"
            elif is_special:
                price_str = format_de(p)
            else:
                price_str = format_de(p)

            # Volumen für Öl + BTC (ab 1000 → 1.000er Punkt)
            rv_str = ""
            if sym in ["CL=F", "BZ=F", "BTC-USD"]:
                try:
                    vol = int(h['Volume'].iloc[-1])
                    rv_str = f"{vol:,}".replace(",", ".")
                except:
                    rv_str = ""

            # Prozentuale Veränderung
            chg = ((p - prev)/prev)*100
            chg_str = f"{chg:+.2f}%"

            results.append({
                "name": name,
                "p": price_str,
                "chg": chg_str,
                "rv": rv_str,
                "al": "warning",  # Nur für CSS
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
        ratio_chg = ((ratio - g['Close'].iloc[-2]/s['Close'].iloc[-2])/ (g['Close'].iloc[-2]/s['Close'].iloc[-2]))*100
        ratio_al = "warning"

    except Exception as e:
        print(f"Fehler Gold/Silber Ratio: {e}")
        ratio = 0
        ratio_chg = 0
        ratio_al = "warning"

    # =========================
    # ÖL ANALYSE (WTI + BRENT)
    # =========================
    oil_data = []
    for oil_sym in ["CL=F", "BZ=F"]:
        oil = get_data(oil_sym, "2d", interval="1h")
        if oil is None or len(oil) < 2:
            oil_data.append({
                "name": oil_sym,
                "price": "",
                "chg": "",
                "vol_now": "",
                "vol_yest": "",
                "al": "danger"
            })
            continue

        try:
            close_today = oil['Close'].iloc[-1]
            close_yest = oil['Close'].iloc[-25]  # ca. gleiche Uhrzeit gestern

            vol_now = int(oil['Volume'].iloc[-1])
            vol_yest = int(oil['Volume'].iloc[-25])

            # Format Zahlen
            price_str = format_de(close_today)
            vol_now_str = f"{vol_now:,}".replace(",", ".")
            vol_yest_str = f"{vol_yest:,}".replace(",", ".")

            chg = ((close_today - close_yest)/close_yest)*100
            chg_str = f"{chg:+.2f}%"

            oil_data.append({
                "name": oil_sym,
                "price": price_str,
                "chg": chg_str,
                "vol_now": vol_now_str,
                "vol_yest": vol_yest_str,
                "al": "warning"
            })

        except Exception as e:
            print(f"Fehler Öl Analyse {oil_sym}: {e}")
            oil_data.append({
                "name": oil_sym,
                "price": "",
                "chg": "",
                "vol_now": "",
                "vol_yest": "",
                "al": "danger"
            })

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
{% if a.rv %}Volumen: {{a.rv}}{% endif %}
</div>
{% endfor %}

{% for o in oil %}
<div class="card border-{{o.al}}">
<h4>{{o.name}} Öl Analyse</h4>
Preis: {{o.price}}<br>
Veränderung: {{o.chg}}<br>
Volumen jetzt: {{o.vol_now}}<br>
Volumen gestern: {{o.vol_yest}}
</div>
{% endfor %}

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
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(debug=True)
