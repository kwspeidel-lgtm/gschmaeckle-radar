from flask import Flask, render_template_string
import yfinance as yf

app = Flask(__name__)

TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "Euro Stoxx 50 (^STOXX50E)": "^STOXX50E",
    "S&P 500 (^GSPC)": "^GSPC",
    "Dow Jones (^DJI)": "^DJI",
    "Nasdaq (^IXIC)": "^IXIC",
    "Gold (GC=F)": "GC=F",
    "Silber (SI=F)": "SI=F",
    "Kupfer (HG=F)": "HG=F",
    "Öl WTI (CL=F)": "CL=F",
    "EUR/USD (EURUSD=X)": "EURUSD=X",
    "Bitcoin (BTC-USD)": "BTC-USD"
}

def get_market_data():
    results, prices = [], {}

    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if h.empty or len(h) < 2: continue

            p, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
            chg = ((p - prev)/prev)*100
            prices[name] = p

            is_fx = "EURUSD" in sym
            is_special = sym in ["HG=F", "CL=F"]
            is_btc = "BTC-USD" in sym

            # ===== FORMAT PREIS =====
            if is_fx:
                price_str = f"{p:.4f}"
            elif is_btc or is_special:
                price_str = "{:,.2f}".format(p)
            else:
                price_str = f"{p:.2f}"

            # ===== VOLUMEN =====
            rv_str = ""
            if is_special or is_btc:
                try:
                    vol = int(h['Volume'].iloc[-1])
                    rv_str = "{:,}".format(vol)
                except:
                    rv_str = ""
            else:
                try:
                    h_v = t.history(period="1mo")
                    cv, av = h_v['Volume'].iloc[-1], h_v['Volume'].iloc[-12:-2].mean()
                    if cv == 0 or (av>0 and cv/av>50):
                        cv = h_v['Volume'].iloc[-2]
                    rv = cv/av if av>0 else 0
                    rv_str = f"{rv:.2f}"
                except:
                    rv_str = ""

            # ===== INTERPRETATION =====
            if chg > 2:
                interp = "stark bullisch"; al="success"
            elif chg > 0.5:
                interp = "leicht bullisch"; al="success"
            elif chg < -2:
                interp = "stark bärisch"; al="danger"
            elif chg < -0.5:
                interp = "leicht bärisch"; al="warning"
            else:
                interp = "neutral"; al="warning"

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

    # ===== GOLD/SILBER RATIO =====
    try:
        g = yf.Ticker("GC=F").history(period="2d")
        s = yf.Ticker("SI=F").history(period="2d")

        ratio = g['Close'].iloc[-1] / s['Close'].iloc[-1]
        ratio_prev = g['Close'].iloc[-2] / s['Close'].iloc[-2]
        ratio_chg = ((ratio - ratio_prev)/ratio_prev)*100

        if ratio_chg > 0.5:
            ratio_al = "success"
        elif ratio_chg < -0.5:
            ratio_al = "danger"
        else:
            ratio_al = "warning"
    except:
        ratio = None; ratio_chg=None; ratio_al="success"

    # ===== ÖL VOLUMEN HEUTE VS GESTERN =====
    try:
        oil = yf.Ticker("CL=F").history(period="5d")

        vol_today = int(oil['Volume'].iloc[-1])
        vol_yesterday = int(oil['Volume'].iloc[-2])

        vol_today_str = "{:,}".format(vol_today)
        vol_yesterday_str = "{:,}".format(vol_yesterday)

        if vol_today > vol_yesterday:
            oil_al = "success"
        elif vol_today < vol_yesterday:
            oil_al = "danger"
        else:
            oil_al = "warning"

    except:
        vol_today_str = ""
        vol_yesterday_str = ""
        oil_al = "warning"

    shortcut2 = {
        "vol_today": vol_today_str,
        "vol_yesterday": vol_yesterday_str,
        "al": oil_al
    }

    return results, ratio, ratio_chg, ratio_al, shortcut2


HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Radar</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0a0a0a;color:#fff;}
.card{background:#161616;padding:10px;margin:5px;border-radius:10px;}
.text-success{color:#39ff14;}
.text-warning{color:#ffcc00;}
.text-danger{color:#ff3131;}
</style>
</head>
<body>

<div class="container">

<h3>Gold/Silber Ratio: {{ratio|round(2)}} ({{ratio_chg|round(2)}}%)</h3>

{% for a in assets %}
<div class="card border-{{a.al}}">
<b>{{a.name}}</b> {{a.chg}}<br>
Preis: {{a.p}}<br>
Vol/RVOL: {{a.rv}}<br>
{{a.interpretation}}
</div>
{% endfor %}

<div class="card border-{{shortcut2.al}}">
<h4>Öl Volumen</h4>
Heute: {{shortcut2.vol_today}}<br>
Gestern: {{shortcut2.vol_yesterday}}
</div>

</div>
</body>
</html>
"""

@app.route("/")
def home():
    assets, ratio, ratio_chg, ratio_al, shortcut2 = get_market_data()
    return render_template_string(HTML, assets=assets, ratio=ratio, ratio_chg=ratio_chg, ratio_al=ratio_al, shortcut2=shortcut2)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
