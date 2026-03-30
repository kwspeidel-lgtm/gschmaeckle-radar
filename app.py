from flask import Flask, render_template_string
import yfinance as yf

app = Flask(__name__)

TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "Euro Stoxx 50 (^STOXX50E)": "^STOXX50E",
    "S&P 500 (^GSPC)": "^GSPC",
    "Gold (GC=F)": "GC=F", 
    "Silber (SI=F)": "SI=F", 
    "Öl WTI (CL=F)": "CL=F", 
    "EUR/USD (EURUSD=X)": "EURUSD=X"
}

def get_market_data():
    results, prices = [], {}
    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="2d")
            if len(h) < 2: continue
            
            p, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            prices[name] = p
            
            h_v = t.history(period="1mo")
            cv, av = h_v['Volume'].iloc[-1], h_v['Volume'].iloc[-12:-2].mean()
            if cv == 0 or (av > 0 and cv/av > 50): cv = h_v['Volume'].iloc[-2]
            rv = cv / av if av > 0 else 0
            
            results.append({
                "name": name, "p": f"{p:.4f}" if "EURUSD" in sym else f"{p:.2f}",
                "chg": f"{chg:+.2f}%", "c_val": chg, "rv": f"{rv:.2f}" if (cv > 0 and "EURUSD" not in sym) else "N/A",
                "al": "danger" if (rv > 3.0 and "EURUSD" not in sym) else "success"
            })
        except: continue
    
    try: ratio = f"{prices['Gold (GC=F)'] / prices['Silber (SI=F)']:.2f}"
    except: ratio = "N/A"
    return results, ratio

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radar v1.5</title><meta name="mobile-web-app-capable" content="yes">
<link rel="icon" href="https://cdn-icons-png.flaticon.com/512/1995/1995531.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body{background:#0a0a0a;color:#fff;font-family:sans-serif;} 
    .neon{color:#39ff14;text-shadow:0 0 5px #39ff14;}
    .card{background:#161616;border-radius:12px;padding:12px;margin-bottom:8px;border:1px solid #333;}
    .ratio-box{border: 1px solid #444; padding: 10px; border-radius: 8px; margin-bottom: 15px; background: #111;}
    .border-danger{border:2px solid #ff3131!important;box-shadow:0 0 8px #ff3131;}
    .border-success{border:1px solid #333!important;}
    .up{color:#00d4ff;}.down{color:#ff3131;}.lbl{color:#888;font-size:0.75rem;}
    .disc{font-size:0.6rem;color:#444;padding:15px;border-top:1px solid #222;margin-top:15px;}
</style></head>
<body><div class="container py-2"><h2 class="text-center neon mb-2">Gschmäckle Radar v1.5 🚀</h2>
<div class="text-center ratio-box"><small class="lbl">GOLD/SILBER RATIO</small><br><span class="h4 neon">{{ ratio }}</span></div>
<div class="row">{% for a in assets %}<div class="col-12 col-md-6"><div class="card border-{{a.al}}">
<div class="d-flex justify-content-between"><h6 class="mb-0">{{a.name}}</h6><span class="{% if a.c_val >= 0 %}up{% else %}down{% endif %} fw-bold">{{a.chg}}</span></div>
<hr style="border-color:#333;margin:8px 0;"><div class="d-flex justify-content-between">
<span class="lbl">PREIS</span><span class="fw-bold">{{a.p}}</span></div><div class="d-flex justify-content-between">
<span class="lbl">RVOL</span><strong class="text-{{a.al}}">{{a.rv}}</strong></div></div></div>{% endfor %}</div>
<div class="disc"><strong>Disclaimer:</strong> Keine Anlageberatung. Daten verzögert. Nutzung auf eigene Gefahr.</div></div></body></html>
"""

@app.route("/")
def home():
    assets, ratio = get_market_data()
    return render_template_string(HTML, assets=assets, ratio=ratio)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
