from flask import Flask, render_template_string, make_response
import yfinance as yf
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# ==========================================
# TRUMP-RELEVANTE TICKER & RVOL LOGIK
# ==========================================
def get_market_data():
    # Nur diese Werte bekommen den Insider-Scanner (RVOL)
    TRUMP_SENSITIVE = {
        "WTI Öl": "CL=F",
        "Gold (USD)": "GC=F",
        "Nasdaq 100": "^IXIC",
        "S&P 500": "^GSPC",
        "Kupfer": "HG=F"
    }
    # Normale Beobachtungswerte (Ohne Blink-Alarm)
    WATCHLIST = {
        "DAX": "^GDAXI",
        "EUR/USD": "EURUSD=X"
    }
    
    results = []
    
    # EUR/USD für Umrechnung holen
    fx = yf.download("EURUSD=X", period="1d", interval="1m", progress=False)
    eur_usd = float(fx['Close'].iloc[-1]) if not fx.empty else 1.0

    # 1. Scanner für Gschmäckle-Werte
    for name, sym in TRUMP_SENSITIVE.items():
        try:
            df = yf.download(sym, period="5d", interval="30m", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            curr_price = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            chg_pct = ((curr_price - prev_close) / prev_close) * 100
            
            # RVOL Berechnung
            curr_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Volume'].mean())
            rvol = curr_vol / avg_vol if avg_vol > 0 else 0
            
            price_display = f"{curr_price:,.2f}"
            if "Gold" in name:
                price_display = f"${curr_price:,.2f} | €{curr_price/eur_usd:,.2f}"

            results.append({
                "name": name, "price": price_display, "chg": f"{chg_pct:+.2f}%",
                "color": "#00ffcc" if chg_pct >= 0 else "#ff3131",
                "rvol": round(rvol, 2),
                "alert": rvol > 3.0, # NUR HIER BLINKT ES
                "is_monitored": True
            })
        except: continue

    # 2. Einfache Watchlist (Kein RVOL nötig)
    for name, sym in WATCHLIST.items():
        try:
            df = yf.download(sym, period="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            curr_price = float(df['Close'].iloc[-1])
            results.append({
                "name": name, "price": f"{curr_price:,.2f}", "chg": "", 
                "color": "#eee", "rvol": None, "alert": False, "is_monitored": False
            })
        except: continue
        
    return results

# ==========================================
# HTML MIT GEZIELTEM ALARM
# ==========================================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background:#0a0a0a; color:#eee; font-family:sans-serif; padding:15px; }
        .card { background:#161616; padding:15px; margin-bottom:12px; border-radius:10px; border-left: 5px solid #444; }
        .chg-val { float: right; font-weight: bold; }
        .rvol-tag { font-size: 0.75em; color: #666; margin-top: 5px; display: block; }
        .insider-alert { 
            border-left-color: #ff0000; 
            background: linear-gradient(90deg, #330000, #161616);
            animation: pulse 1s infinite;
        }
        @keyframes pulse { 50% { background: #440000; } }
        .alert-text { color: #ff0000; font-weight: bold; font-size: 0.7em; }
    </style>
</head>
<body>
    <h2>🔍 Trump-Montag Radar</h2>
    {% for a in data %}
    <div class="card {% if a.alert %}insider-alert{% endif %}">
        <span class="chg-val" style="color:{{a.color}}">{{a.chg}}</span>
        <b>{{a.name}}</b><br>
        <span>{{a.price}}</span>
        {% if a.is_monitored %}
        <span class="rvol-tag">
            {% if a.alert %}<span class="alert-text">⚠️ INSIDER-MOVE? </span>{% endif %}
            RVOL: {{a.rvol}}
        </span>
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route("/")
def home():
    data = get_market_data()
    resp = make_response(render_template_string(HTML, data=data))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Refresh"] = "45"
    return resp

if __name__ == "__main__":
    app.run(debug=True)
