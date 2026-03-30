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
    "Dow Jones (^DJI)": "^DJI",
    "Nasdaq (^IXIC)": "^IXIC",
    "Gold (GC=F)": "GC=F",
    "Silber (SI=F)": "SI=F",
    "Kupfer (HG=F)": "HG=F",
    "Öl WTI (CL=F)": "CL=F",
    "EUR/USD (EURUSD=X)": "EURUSD=X",
    "Bitcoin (BTC-USD)": "BTC-USD"
}

# =========================
# Markt-Daten + Interpretation
# =========================
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
            is_copper = "HG=F" in sym
            is_oil = "CL=F" in sym
            is_index = sym in ["^GDAXI","^STOXX50E","^GSPC","^DJI","^IXIC"]

            # RVOL / Volumen / Kontrakte
            rv_str = ""
            interp_rvol = ""
            if is_copper or is_oil:
                try:
                    h_v = t.history(period="5d")
                    rv_str = str(int(h_v['Volume'].iloc[-1])) if not h_v.empty else ""
                except: rv_str = ""
            elif is_fx:
                rv_str = ""
            else:
                h_v = t.history(period="1mo")
                cv, av = h_v['Volume'].iloc[-1], h_v['Volume'].iloc[-12:-2].mean()
                if cv == 0 or (av>0 and cv/av>50): cv = h_v['Volume'].iloc[-2]
                rv = cv/av if av>0 else 0
                rv_str = f"{rv:.2f}"
                if rv > 3.0: interp_rvol = "stark auffällig"; al = "danger"
                elif rv > 1.5: interp_rvol = "leicht auffällig"; al = "warning"
                else: interp_rvol = "normal"; al = "success"

            # Indices Ampel / Interpretation
            if is_index:
                if chg>2: al="success" if chg>0 else "danger"; interp_chg="starker Anstieg" if chg>0 else "starker Rückgang"
                elif chg>0.5: al="success" if chg>0 else "warning"; interp_chg="leichter Anstieg" if chg>0 else "leichter Rückgang"
                else: al="success" if chg>0 else "warning"; interp_chg="neutral"
            else:
                if interp_rvol=="":
                    if chg>2: interp_chg="starker Anstieg"; al="success"
                    elif chg>0.5: interp_chg="leichter Anstieg"; al="success"
                    elif chg<-2: interp_chg="starker Rückgang"; al="danger"
                    elif chg<-0.5: interp_chg="leichter Rückgang"; al="warning"
                    else: interp_chg="neutral"
                else:
                    interp_chg=f"{interp_chg} / {interp_rvol}"

            results.append({
                "name": name,
                "p": f"{p:.4f}" if is_fx else f"{p:.2f}",
                "chg": f"{chg:+.2f}%",
                "c_val": chg,
                "rv": rv_str,
                "al": al,
                "interpretation": interp_chg
            })
        except:
            continue

    # =========================
    # Gold/Silber-Ratio inkl. Vortag
    # =========================
    try:
        g_v = next((v for k,v in prices.items() if "Gold" in k), None)
        s_v = next((v for k,v in prices.items() if "Silber" in k), None)
        ratio = g_v / s_v if g_v and s_v else None

        h_gold = yf.Ticker("GC=F").history(period="2d")
        h_silver = yf.Ticker("SI=F").history(period="2d")
        ratio_prev = (h_gold['Close'].iloc[-2]/h_silver['Close'].iloc[-2]) if len(h_gold)>=2 and len(h_silver)>=2 else None
        ratio_chg = ((ratio - ratio_prev)/ratio_prev)*100 if ratio and ratio_prev else None

        if ratio_chg is not None:
            if ratio_chg>0.5: ratio_al="success"
            elif ratio_chg<-0.5: ratio_al="danger"
            else: ratio_al="warning"
        else:
            ratio_al="success"
    except:
        ratio = None; ratio_chg = None; ratio_al="success"

    # =========================
    # Öl Analyse Panel
    # =========================
    try:
        oil = yf.Ticker("CL=F").history(period="2d")
        oil_vol = int(oil['Volume'].iloc[-1]) if len(oil)>=1 else None
        oil_vol_prev = int(oil['Volume'].iloc[-2]) if len(oil)>=2 else None

        if oil_vol and oil_vol_prev:
            if oil_vol>oil_vol_prev: oil_al="success"
            elif oil_vol<oil_vol_prev: oil_al="danger"
            else: oil_al="warning"
        else:
            oil_al="success"

    except:
        oil_vol=None; oil_vol_prev=None; oil_al="success"

    oil_analysis = {
        "oil_vol": oil_vol,
        "oil_vol_prev": oil_vol_prev,
        "al": oil_al
    }

    return results, ratio, ratio_chg, ratio_al, oil_analysis

# =========================
# HTML Template
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gschmäckle Radar v4.1</title>
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
<h2 class="text-center neon mb-2">Gschmäckle Radar v4.1 🚀</h2>

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

<!-- Öl Analyse Panel -->
<div class="card my-3 border-{{oil_analysis.al}}">
<h5 class="text-center neon">Öl Analyse</h5>
<hr style="border-color:#333;margin:8px 0;">
<div class="d-flex justify-content-between align-items-center">
<span class="lbl">Volumen heute</span>
<span class="p-val">{{oil_analysis.oil_vol}} {% if oil_analysis.oil_vol_prev %}(vs. {{oil_analysis.oil_vol_prev}}){% endif %}</span>
</div>
<div class="d-flex justify-content-between align-items-center">
<span class="lbl">Ampel Öl</span>
<span class="text-{{oil_analysis.al}} fw-bold">{{oil_analysis.al|capitalize}}</span>
</div>
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
    assets, ratio, ratio_chg, ratio_al, oil_analysis = get_market_data()
    return render_template_string(HTML, assets=assets, ratio=ratio, ratio_chg=ratio_chg, ratio_al=ratio_al, oil_analysis=oil_analysis)

# =========================
# App starten
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
