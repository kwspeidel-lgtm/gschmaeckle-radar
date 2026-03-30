from flask import Flask, render_template_string
import yfinance as yf

app = Flask(__name__)

# =========================
# Tickerliste
# =========================
TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "Euro Stoxx 50 (^STOXX50E)": "^STOXX50E",
    "S&P 500 (^GSPC)": "^GSPC",
    "Gold (GC=F)": "GC=F",
    "Silber (SI=F)": "SI=F",
    "Kupfer (HG=F)": "HG=F",
    "Öl WTI (CL=F)": "CL=F",
    "EUR/USD (EURUSD=X)": "EURUSD=X",
    "Bitcoin (BTC-USD)": "BTC-USD"
}

# =========================
# Daten abholen + Interpretation + Ampel
# =========================
def get_market_data():
    results, prices = [], {}

    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if h.empty or len(h) < 2:
                continue

            p, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            prices[name] = p

            is_fx = "EURUSD" in sym
            is_copper = "HG=F" in sym
            is_oil = "CL=F" in sym

            # RVOL & Ampel
            if is_fx or is_copper:
                rv_str = ""
                interp_rvol = ""
            elif is_oil:
                # Versuch, Kontrakte/Open Interest abzurufen
                try:
                    h_v = t.history(period="5d")
                    rv_str = str(h_v['Volume'].iloc[-1]) if not h_v.empty else ""
                except:
                    rv_str = ""
                interp_rvol = ""
            else:
                h_v = t.history(period="1mo")
                cv, av = h_v['Volume'].iloc[-1], h_v['Volume'].iloc[-12:-2].mean()
                if cv == 0 or (av > 0 and cv/av > 50):
                    cv = h_v['Volume'].iloc[-2]
                rv = cv / av if av > 0 else 0
                rv_str = f"{rv:.2f}"

                if rv > 3.0:
                    interp_rvol = "stark auffällig"
                    al = "danger"
                elif rv > 1.5:
                    interp_rvol = "leicht auffällig"
                    al = "warning"
                else:
                    interp_rvol = "normal"
                    al = "success"

            # Interpretation Preisveränderung
            if chg > 2:
                interp_chg = "starker Anstieg"
            elif chg > 0.5:
                interp_chg = "leichter Anstieg"
            elif chg < -2:
                interp_chg = "starker Rückgang"
            elif chg < -0.5:
                interp_chg = "leichter Rückgang"
            else:
                interp_chg = "neutral"

            # Ampel für Assets ohne RVOL
            if rv_str in ["", None]:
                if interp_chg in ["starker Rückgang"]:
                    al = "danger"
                elif interp_chg in ["leichter Rückgang"]:
                    al = "warning"
                else:
                    al = "success"

            interp = f"{interp_chg}" if interp_rvol=="" else f"{interp_chg} / {interp_rvol}"

            results.append({
                "name": name,
                "p": f"{p:.4f}" if is_fx else f"{p:.2f}",
                "chg": f"{chg:+.2f}%",
                "c_val": chg,
                "rv": rv_str,
                "al": al,
                "interpretation": interp
            })

        except:
            continue

    # =========================
    # Gold/Silber-Ratio
    # =========================
    try:
        g_v = next((v for k,v in prices.items() if "Gold" in k), None)
        s_v = next((v for k,v in prices.items() if "Silber" in k), None)
        ratio = g_v / s_v if g_v and s_v else None

        h_gold = yf.Ticker("GC=F").history(period="2d")
        h_silver = yf.Ticker("SI=F").history(period="2d")
        ratio_prev = (h_gold['Close'].iloc[-2] / h_silver['Close'].iloc[-2]) if len(h_gold)>=2 and len(h_silver)>=2 else None
        ratio_chg = ((ratio - ratio_prev)/ratio_prev)*100 if ratio and ratio_prev else None

        if ratio_chg is not None:
            if ratio_chg > 0.5:
                ratio_al = "success"
            elif ratio_chg < -0.5:
                ratio_al = "danger"
            else:
                ratio_al = "warning"
        else:
            ratio_al = "success"

    except:
        ratio = None
        ratio_chg = None
        ratio_al = "success"

    return results, ratio, ratio_chg, ratio_al

# =========================
# HTML Template
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gschmäckle Radar v2.5</title>
<link rel="icon" href="https://cdn-icons-png.flaticon.com/512/1995/1995531.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#0a0a0a;color:#fff;font-family:sans-serif;} 
.neon{color:#39ff14;text-shadow:0 0 5px #39ff14;}
.card{background:#161616;border-radius:12px;padding:12px;margin-bottom:8px;border:1px solid #333;}
.ratio-box{border: 2px solid #444; padding: 10px; border-radius: 8px; margin-bottom: 15px; background: #111;}
.up{color:#00d4ff;}.down{color:#ff3131;}
.p-val{color:#ffffff !important; font-weight:bold; font-size:1.1rem;}
.lbl{color:#888;font-size:0.75rem;}
.disc{font-size:0.7rem;color:#ff6666;padding:15px;border-top:2px solid #222;margin-top:15px;}
.text-success{color:#39ff14 !important;}
.text-warning{color:#ffcc00 !important;}
.text-danger{color:#ff3131 !important;}
</style>
</head>
<body>
<div class="container py-2">
<h2 class="text-center neon mb-2">Gschmäckle Radar v2.5 🚀</h2>

<div class="text-center ratio-box border-{{ratio_al}}">
<small class="lbl">GOLD/SILBER RATIO</small><br>
<span class="h4 neon">{{ ratio|round(2) }}</span>
{% if ratio_chg %}
  <small class="{% if ratio_chg>0 %}up{% elif ratio_chg<0 %}down{% endif %}">
    ({{ ratio_chg|round(2) }}%)
  </small>
{% endif %}
</div>

<div class="row">
{% for a in assets %}
<div class="col-12 col-md-6">
<div class="card border-{{a.al}}">
<div class="d-flex justify-content-between align-items-center">
<h6 class="mb-0" style="color:#39ff14;">{{a.name}}</h6>
<span class="{% if a.c_val >= 0 %}up{% else %}down{% endif %} fw-bold">{{a.chg}}</span>
</div>
<hr style="border-color:#333;margin:8px 0;">
<div class="d-flex justify-content-between align-items-center">
<span class="lbl">PREIS</span><span class="p-val">{{a.p}}</span>
</div>
<div class="d-flex justify-content-between align-items-center">
<span class="lbl">RVOL / Kontrakte</span>
<strong class="text-{{a.al}}">{{a.rv}}</strong>
</div>
<div class="d-flex justify-content-between align-items-center">
<span class="lbl">Interpretation</span>
<span class="text-{{a.al}} fw-bold">{{a.interpretation}}</span>
</div>
</div>
</div>
{% endfor %}
</div>

<div class="disc">
<strong>Disclaimer:</strong> Keine Anlageberatung. Alle Daten verzögert. Nutzung auf eigene Gefahr.
</div>
</div>
</body>
</html>
"""

# =========================
# Flask Route
# =========================
@app.route("/")
def home():
    assets, ratio, ratio_chg, ratio_al = get_market_data()
    return render_template_string(HTML, assets=assets, ratio=ratio, ratio_chg=ratio_chg, ratio_al=ratio_al)

# =========================
# App starten
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
