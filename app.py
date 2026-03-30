from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

# --- KONFIGURATION & LOGIK ---
TICKERS = {
    "Gold (GC=F)": "GC=F",
    "Silber (SI=F)": "SI=F",
    "Öl WTI (CL=F)": "CL=F",
    "Öl Brent (BZ=F)": "BZ=F",
    "S&P 500 (^GSPC)": "^GSPC"
}

RVOL_THRESHOLD = 3.0
GOLD_SILVER_TARGET = 64.41

def get_asset_data():
    results = []
    today = datetime.now()
    for name, ticker_symbol in TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="1mo", interval="1d")
            if hist.empty:
                results.append({"name": name, "status": "error", "message": "Keine Daten"})
                continue
            current_volume = hist['Volume'].iloc[-1]
            avg_10d_volume = hist['Volume'].iloc[-11:-1].mean()
            rvol = current_volume / avg_10d_volume if avg_10d_volume > 0 else 0
            alert = "danger" if rvol > RVOL_THRESHOLD else "success"
            sentiment = "PANIK / GIER" if rvol > RVOL_THRESHOLD else "Normal"
            price = hist['Close'].iloc[-1]
            results.append({
                "name": name, "status": "ok", "price": f"{price:.2f}",
                "rvol": f"{rvol:.2f}", "avg_vol": int(avg_10d_volume),
                "alert": alert, "sentiment": sentiment
            })
        except:
            results.append({"name": name, "status": "error", "message": "Fehler"})
    return results

def get_analysis(assets):
    try:
        g = float(next(a['price'] for a in assets if "Gold" in a['name']))
        s = float(next(a['price'] for a in assets if "Silber" in a['name']))
        b = float(next(a['price'] for a in assets if "Brent" in a['name']))
        w = float(next(a['price'] for a in assets if "WTI" in a['name']))
        return {"ratio": f"{g/s:.2f}" if s > 0 else "N/A", "spread": f"{b-w:.2f}"}
    except:
        return {"ratio": "N/A", "spread": "N/A"}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gschmäckle Radar</title>
    
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    <link rel="icon" type="image/png" href="https://cdn-icons-png.flaticon.com/512/1995/1995531.png">
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: sans-serif; }
        .neon-text { color: #39ff14; text-shadow: 0 0 5px #39ff14; }
        .scanner-card { background-color: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 15px; border: 1px solid #333; }
        .border-danger { border: 2px solid #ff3131 !important; box-shadow: 0 0 15px #ff3131; }
        .border-success { border: 1px solid #39ff14 !important; }
        footer { font-size: 0.7rem; color: #666; text-align: center; margin-top: 30px; padding: 20px; }
    </style>
</head>
<body>
<div class="container py-4">
    <h1 class="text-center neon-text mb-4">Gschmäckle Radar v1.0 🚀</h1>
    <div class="row mb-4 text-center">
        <div class="col-6">
            <div class="p-2 border border-secondary rounded">
                <small class="text-muted">GOLD/SILBER RATIO</small><br>
                <span class="h4">{{ analysis.ratio }}</span>
            </div>
        </div>
        <div class="col-6">
            <div class="p-2 border border-secondary rounded">
                <small class="text-muted">ÖL SPREAD (B/W)</small><br>
                <span class="h4">{{ analysis.spread }} USD</span>
            </div>
        </div>
    </div>
    <div class="row">
        {% for asset in assets %}
        <div class="col-12 col-md-6 col-lg-4">
            <div class="scanner-card border-{{ asset.alert }}">
                <h5>{{ asset.name }}</h5>
                <hr style="border-color: #444;">
                <div class="d-flex justify-content-between">
                    <span>Preis:</span> <strong>{{ asset.price }}</strong>
                </div>
                <div class="d-flex justify-content-between mt-2">
                    <span>RVOL:</span> <strong class="text-{{ asset.alert }} h5">{{ asset.rvol }}</strong>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
<footer>
    Hinweis: Das 'Gschmäckle Radar' zeigt algorithmische Volumen-Anomalien. Nutzung auf eigene Gefahr.
</footer>
</body>
</html>
"""

@app.route("/")
def home():
    assets = get_asset_data()
    analysis = get_analysis(assets)
    return render_template_string(HTML_TEMPLATE, assets=assets, analysis=analysis)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
