from flask import Flask, render_template_string, make_response
import yfinance as yf
import time
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)

# ==========================================
# DATEN-FUNKTION (ROBUST GEGEN MULTI-INDEX)
# ==========================================
def get_data(sym, period="7d", interval="1h"):
    try:
        # Wir laden die Daten und bereinigen den Header (Multi-Index Fix)
        df = yf.download(sym, period=period, interval=interval, progress=False)
        
        if df.empty:
            return None
            
        # Falls yfinance mehrere Spalten-Ebenen liefert (Ticker im Header), flach machen
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        return df
    except Exception as e:
        print(f"Fehler bei {sym}: {e}")
        return None

# ==========================================
# FORMATIERUNG & TICKER
# ==========================================
TICKERS = {
    "DAX": "^GDAXI", "S&P 500": "^GSPC", 
    "Gold": "GC=F", "Silber": "SI=F",
    "EUR/USD": "EURUSD=X"
}

def format_de(zahl):
    try:
        return f"{float(zahl):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "N/A"

# ==========================================
# HAUPTLOGIK
# ==========================================
def get_market_data():
    results = []
    oil_summary = []
    ratio = 0.0

    # 1. Standard-Assets
    for name, sym in TICKERS.items():
        df = get_data(sym, "5d", "1h")
        if df is not None and len(df) > 1:
            p = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            p_str = f"{p:.4f}" if "EURUSD" in sym else format_de(p)
            results.append({
                "name": name, "p": p_str, "chg": f"{chg:+.2f}%"
            })

    # 2. Gold/Silber Ratio
    try:
        g_df = get_data("GC=F", "2d", "1h")
        s_df = get_data("SI=F", "2d", "1h")
        if g_df is not None and s_df is not None:
            ratio = float(g_df['Close'].iloc[-1] / s_df['Close'].iloc[-1])
    except:
        ratio = 0.0

    # 3. ÖL-ANALYSE (Dein 24h RVOL-Check)
    for name, sym in [("WTI", "CL=F"), ("Brent", "BZ=F")]:
        df = get_data(sym, "7d", "1h")
        if df is not None and len(df) > 25:
            try:
                now_idx = df.index[-1]
                target_time = now_idx - timedelta(hours=24)
                
                # Finde die Bar, die gestern am nächsten zur selben Zeit war
                idx_yest = df.index.get_indexer([target_time], method='nearest')[0]
                
                v_now = float(df['Volume'].iloc[-1])
                v_yest = float(df['Volume'].iloc[idx_yest])
                p_now = float(df['Close'].iloc[-1])
                
                rvol = v_now / v_yest if v_yest > 0 else 0
                
                # Alarm-Status für RVOL > 3 (Dein Shortcut)
                status = "danger" if rvol > 3 else "warning"
                
                oil_summary.append({
                    "name": name,
                    "price": format_de(p_now),
                    "v_now": f"{int(v_now):,}".replace(",", "."),
                    "v_yest": f"{int(v_yest):,}".replace(",", "."),
                    "rvol": f"{rvol:.2f}",
                    "al": status
                })
            except Exception as e:
                print(f"Öl Error {name}: {e}")

    return results, ratio, oil_summary

# ==========================================
# HTML-DESIGN (DARK MODE)
# ==========================================
HTML = """
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Radar Pro</title>
    <style>
        body { background:#0a0a0a; color:#eee; font-family:sans-serif; padding:15px; }
        .card { background:#161616; padding:12px; margin-bottom:10px; border-radius:8px; border-left:5px solid #444; }
        .border-warning { border-left-color: #ffcc00; }
        .border-danger { border-left-color: #ff3131; background: #2a1111; }
        h3, h4 { margin: 5px 0; color: #fff; }
        .rvol-val { font-size: 1.2em; font-weight: bold; color: #00ffcc; }
        .mini { font-size: 0.85em; color: #888; }
    </style>
</head>
<body>
    <h3>Gschmäckle Radar PRO</h3>
    <p>Gold/Silber Ratio: <b>{{ratio|round(2)}}</b></p>
    
    <hr style="border:0; border-top:1px solid #333; margin:15px 0;">

    {% for o in oil %}
    <div class="card border-{{o.al}}">
        <h4>{{o.name}} Öl (Uhrzeit-Check)</h4>
        Preis: <b>{{o.price}}</b> | RVOL: <span class="rvol-val">{{o.rvol}}</span><br>
        <span class="mini">Volumen Jetzt: {{o.v_now}} vs. Gestern: {{o.v_yest}}</span>
    </div>
    {% endfor %}

    <h4>Markt-Übersicht</h4>
    {% for a in assets %}
    <div class="card">
        <b>{{a.name}}</b>: {{a.p}} ({{a.chg}})
    </div>
    {% endfor %}
</body>
</html>
"""

# ==========================================
# FLASK ROUTE
# ==========================================
@app.route("/")
def home():
    assets, ratio, oil = get_market_data()
    resp = make_response(render_template_string(HTML, assets=assets, ratio=ratio, oil=oil))
    resp.headers["Refresh"] = "60" # Auto-Update jede Minute
    return resp

if __name__ == "__main__":
    app.run(debug=True)
