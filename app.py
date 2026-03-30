from flask import Flask, render_template_string
import yfinance as yf
from datetime import datetime

app = Flask(__name__)

TICKERS = {
    "DAX (^GDAXI)": "^GDAXI", "Gold (GC=F)": "GC=F", "Silber (SI=F)": "SI=F", 
    "Öl WTI (CL=F)": "CL=F", "S&P 500 (^GSPC)": "^GSPC", "EUR/USD (EURUSD=X)": "EURUSD=X"
}

def get_data():
    results, prices = [], {}
    for name, sym in TICKERS.items():
        try:
            h = yf.Ticker(sym).history(period="1mo", interval="1d")
            if h.empty: continue
            curr_v, avg_v = h['Volume'].iloc[-1], h['Volume'].iloc[-12:-2].mean()
            # Glitch-Filter
            if curr_v == 0 or (avg_v > 0 and curr_v / avg_v > 50): 
                price, curr_v = h['Close'].iloc[-2], h['Volume'].iloc[-2]
            else: price = h['Close'].iloc[-1]
            
            prices[name] = price
            rvol = curr_v / avg_v if avg_v > 0 else 0
            is_fx = "EURUSD" in sym
            
            if is_fx or curr_v <= 0: color = "success"
            elif rvol > 3.0: color = "danger"
            elif rvol > 1.5: color = "warning"
            else: color = "success"

            results.append({
                "name": name, "price": f"{price:.4f}" if is_fx else f"{price:.2f}",
                "rvol": f"{rvol:.2f}" if (not is_fx and curr_v > 0) else "N/A",
                "color": color
            })
        except: results.append({"name": name, "price": "Error", "rvol": "0", "color": "secondary"})
    
    ratio = f"{prices.get('Gold (GC=F)', 0) / prices.get('Silber (SI=F)', 1):.2f}"
    return results, ratio

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="60"> <title>Gschmäckle Radar v1.7</title><meta name="mobile-web-app-capable" content="yes">
<link rel="icon" href="https://cdn-icons-png.flaticon.com/512/1995/1995531.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body{background:#121212;color:#ffffff;font-family:sans-serif;}
    .neon{color:#39ff14;text-shadow:0 0 5px #39ff14;}
    .card{background:#1e1e1e;border-radius:12px;padding:15px;margin-bottom:10px;border:1px solid #333;}
    .ratio-box{border: 1px solid #444; padding: 15px; border-radius: 8px; margin-bottom: 20px; background: #1a1a1a;}
    .border-danger{border:2px solid #ff3131!important;box-shadow:0 0 10px #ff3131;}
    .border-warning{border:2px solid #ffcc00!important;box-shadow:0 0 10px #ffcc00;}
    .border-success{border:1px solid #39ff14!important;}
    .disclaimer{background:#1a1a1a; padding:12px; border-radius:8px; font-size:0.75rem; border:1px solid #333; margin-top:15px; color:#aaa;}
</style></head>
<body>
<div class="container py-3">
    <h2 class="text-center neon mb-3">Gschmäckle Radar v1.7 🚀</h2>
    <div class="text-center ratio-box">
        <small class="text-muted">GOLD/SILBER RATIO (ZIEL: 64.41)</small><br>
        <span class="h3 neon">{{ ratio }}</span>
    </div>
    <div class="row">
        {% for a in assets %}
        <div class="col-12 col-md-6">
            <div class="card border-{{a.color}}">
                <h5 class="neon">{{a.name}}</h5>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="text-muted">Preis:</span><span class="h5 mb-0" style="color:white;">{{a.price}}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-1">
                    <span class="text-muted">RVOL:</span><strong class="text-{{a.color}}">{{a.rvol}}</strong>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    <div class="disclaimer">
        🚦 <b>Live-Check:</b> Seite lädt alle 60 Sek. neu. Daten verzögert.<br>
        <b>Letztes Update:</b> {{ now }}
    </div>
</div>
</body></html>
"""

@app.route("/")
def home():
    assets, ratio = get_data()
    return render_template_string(HTML, assets=assets, ratio=ratio, now=datetime.now().strftime("%H:%M:%S"))

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000)
