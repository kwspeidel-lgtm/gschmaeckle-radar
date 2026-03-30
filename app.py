from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd

app = Flask(__name__)

# Ticker-Liste inklusive DAX und EUR/USD
TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "Gold (GC=F)": "GC=F", 
    "Silber (SI=F)": "SI=F", 
    "Öl WTI (CL=F)": "CL=F", 
    "S&P 500 (^GSPC)": "^GSPC",
    "EUR/USD (EURUSD=X)": "EURUSD=X"
}
RVOL_LIMIT = 3.0

def get_clean_data():
    results = []
    prices = {}
    for name, sym in TICKERS.items():
        try:
            h = yf.Ticker(sym).history(period="1mo", interval="1d")
            if len(h) < 12: continue
            
            # Montags-Glitch Schutz
            curr_v = h['Volume'].iloc[-1]
            avg_v = h['Volume'].iloc[-12:-2].mean()
            
            # Fix für Yahoo-Fehler oder Handelsruhe
            if curr_v == 0 or (avg_v > 0 and curr_v / avg_v > 50): 
                curr_v = h['Volume'].iloc[-2]
                price = h['Close'].iloc[-2]
            else:
                price = h['Close'].iloc[-1]

            prices[name] = price
            rvol = curr_v / avg_v if avg_v > 0 else 0
            
            # Währungen und Indizes haben bei Yahoo oft kein Volumen, daher N/A Schutz
            is_currency = "EURUSD" in sym
            r_disp = f"{rvol:.2f}" if (not is_currency and curr_v > 0) else "N/A"
            
            results.append({
                "name": name, 
                "price": f"{price:.4f}" if is_currency else f"{price:.2f}", 
                "rvol": r_disp, 
                "alert": "danger" if (rvol > RVOL_LIMIT and not is_currency and curr_v > 0) else "success"
            })
        except: 
            results.append({"name": name, "price": "Check...", "rvol": "0", "alert": "secondary"})
    
    # Gold/Silber Ratio berechnen
    try:
        ratio = f"{prices['Gold (GC=F)'] / prices['Silber (SI=F)']:.2f}"
    except:
        ratio = "N/A"
        
    return results, ratio

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gschmäckle Radar</title><meta name="mobile-web-app-capable" content="yes">
<link rel="icon" href="https://cdn-icons-png.flaticon.com/512/1995/1995531.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body{background:#121212;color:#e0e0e0;font-family:sans-serif;} 
    .neon{color:#39ff14;text-shadow:0 0 5px #39ff14;}
    .card{background:#1e1e1e;border-radius:12px;padding:15px;margin-bottom:10px;border:1px solid #333;}
    .ratio-box{border: 1px solid #444; padding: 10px; border-radius: 8px; margin-bottom: 20px; background: #1a1a1a;}
    .border-danger{border:2px solid #ff3131!important;box-shadow:0 0 10px #ff3131;}
    .border-success{border:1px solid #39ff14!important;}
</style></head>
<body>
<div class="container py-3">
    <h2 class="text-center neon mb-3">Gschmäckle Radar v1.3 🚀</h2>
    <div class="text-center ratio-box">
        <small class="text-muted">GOLD/SILBER RATIO</small><br>
        <span class="h3">{{ ratio }}</span>
    </div>
    <div class="row">
        {% for a in assets %}
        <div class="col-12 col-md-6">
            <div class="card border-{{a.alert}}">
                <h5 style="color:#39ff14;">{{a.name}}</h5>
                <div class="d-flex justify-content-between"><span>Preis:</span><strong>{{a.price}}</strong></div>
                <div class="d-flex justify-content-between"><span>RVOL:</span><strong class="text-{{a.alert}}">{{a.rvol}}</strong></div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
<footer class="text-center mt-4" style="font-size:0.7rem;color:#666;">Filter: DAX integriert & Montags-Glitch-Schutz aktiv.</footer>
</body></html>
"""

@app.route("/")
def home():
    assets, ratio = get_clean_data()
    return render_template_string(HTML, assets=assets, ratio=ratio)

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000)

