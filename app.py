from flask import Flask, render_template_string
import yfinance as yf

app = Flask(__name__)

# Ticker-Liste v1.4
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
            ticker = yf.Ticker(sym)
            h = ticker.history(period="1mo", interval="1d")
            if h.empty: continue
            
            # Preis & Volumen (Montags-Logik)
            curr_v = h['Volume'].iloc[-1]
            avg_v = h['Volume'].iloc[-12:-2].mean()
            
            if curr_v == 0 or (avg_v > 0 and curr_v / avg_v > 50): 
                price = h['Close'].iloc[-2]
                curr_v = h['Volume'].iloc[-2]
            else:
                price = h['Close'].iloc[-1]

            prices[name] = price
            rvol = curr_v / avg_v if avg_v > 0 else 0
            
            is_fx = "EURUSD" in sym
            r_disp = f"{rvol:.2f}" if (not is_fx and curr_v > 0) else "N/A"
            
            results.append({
                "name": name, 
                "price": f"{price:.4f}" if is_fx else f"{price:.2f}", 
                "rvol": r_disp, 
                "alert": "danger" if (rvol > RVOL_LIMIT and not is_fx and curr_v > 0) else "success"
            })
        except: 
            results.append({"name": name, "price": "Fehler", "rvol": "0", "alert": "secondary"})
    
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
    body{background:#121212;color:#ffffff;font-family:sans-serif;} 
    .neon{color:#39ff14;text-shadow:0 0 5px #39ff14;}
    .card{background:#1e1e1e;border-radius:12px;padding:15px;margin-bottom:10px;border:1px solid #333;}
    .ratio-box{border: 1px solid #444; padding: 15px; border-radius: 8px; margin-bottom: 20px; background: #1a1a1a;}
    .border-danger{border:2px solid #ff3131!important;box-shadow:0 0 10px #ff3131;}
    .border-success{border:1px solid #39ff14!important;}
    .price-text{color: #ffffff !important; font-size: 1.2rem; font-weight: bold;}
    .label-text{color: #aaaaaa;}
</style></head>
<body>
<div class="container py-3">
    <h2 class="text-center neon mb-3">Gschmäckle Radar v1.4 🚀</h2>
    <div class="text-center ratio-box">
        <small class="label-text">GOLD/SILBER RATIO</small><br>
        <span class="h3 neon">{{ ratio }}</span>
    </div>
    <div class="row">
        {% for a in assets %}
        <div class="col-12 col-md-6">
            <div class="card border-{{a.alert}}">
                <h5 class="neon">{{a.name}}</h5>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="label-text">Preis:</span><span class="price-text">{{a.price}}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-1">
                    <span class="label-text">RVOL:</span><strong class="text-{{a.alert}}">{{a.rvol}}</strong>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
</body></html>
"""

@app.route("/")
def home():
    assets, ratio = get_clean_data()
    return render_template_string(HTML, assets=assets, ratio=ratio)

if __name__ == "__main__": app.run(host="0.0.0.0", port=5000)
