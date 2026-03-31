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
        # Wir laden die Daten und flachen den Multi-Index ab
        df = yf.download(sym, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Fehler bei {sym}: {e}")
        return None

# ==========================================
# TICKER-DEFINITION (ERWEITERT)
# ==========================================
TICKERS = {
    "DAX": "^GDAXI",
    "NASDAQ 100": "^IXIC",
    "S&P 500": "^GSPC",
    "Euro Stoxx 50": "^STOXX50E",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Kupfer": "HG=F",
    "Gold": "GC=F",
    "Silber": "SI=F",
    "Bitcoin": "BTC-USD",
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

    # 1. Alle Assets (Inkl. Kupfer, Nasdaq, Asien)
    for name, sym in TICKERS.items():
        # Wir laden 5 Tage, um sicher den letzten Schlusskurs zu haben (Wochenende/Feiertag)
        df = get_data(sym, "5d", "1h")
        if df is not None and len(df) >= 2:
            try:
                p = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2])
                chg = ((p - prev) / prev) * 100
                
                # Spezialformatierung für FX und Krypto
                if "EURUSD" in sym:
                    p_str = f"{p:.4f}"
                elif "BTC" in sym:
                    p_str = f"{int(p):,}".replace(",", ".")
                else:
                    p_str = format_de(p)
                
                results.append({
                    "name": name, 
                    "p": p_str, 
                    "chg": f"{chg:+.2f}%",
                    "color": "#00ff00" if chg >= 0 else "#ff4444"
                })
            except: continue

    # 2. Gold/Silber Ratio
    try:
        g_df = get_data("GC=F", "2d", "1h")
        s_df = get_data("SI=F", "2d", "1h")
        if g_df is not None and s_df is not None:
            ratio = float(g_df['Close'].iloc[-1] / s_df['Close'].iloc[-1])
    except:
        ratio = 0.0

    # 3. ÖL-ANALYSE (RVOL Check)
    for name, sym in [("WTI", "CL=F"), ("Brent", "BZ=F")]:
        df = get_data(sym, "7d", "1h")
        if df is not None and len(df) > 25:
            try:
                now_idx = df.index[-1]
                target_time = now_idx - timedelta(hours=24)
                idx_yest = df.index.get_indexer([target_time], method='nearest')[0]
                
                v_now = float(df['Volume'].iloc[-1])
                v_yest = float(df['Volume'].iloc[idx_yest])
                rvol = v_now / v_yest if v_yest > 0 else 0
                
                oil_summary.append({
                    "name": name,
                    "price": format_de(df['Close'].iloc[-1]),
                    "v_now": f"{int(v_now):,}".replace(",", "."),
                    "v_yest": f"{int(v_yest):,}".replace(",", "."),
                    "rvol": f"{rvol:.2f}",
                    "al": "danger" if rvol > 3 else "warning"
                })
            except: continue

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
        .card { background:#161616; padding:12px; margin-bottom:8px; border-radius:8px; border-left:4px solid #444; }
        .border-warning { border-left-color: #ffcc00; }
        .border-danger { border-left-color: #ff3131; background: #2a1111; }
        h3, h4 { margin: 5px 0; color: #fff; }
        .rvol-val { font-size: 1.1em; font-weight: bold; color: #00ffcc; }
        .chg-val { font-weight: bold; float: right; }
        .mini { font-size: 0.8em; color: #777; }
        hr { border:0; border-top:1px solid #333; margin:15px 0; }
    </style>
</head>
<body>
    <h3>Gschmäckle Radar PRO</h3>
    <p>Gold/Silber Ratio: <b style="color:#ffcc00;">{{ratio|round(2)}}</b></p>
    
    <hr>

    {% for o in oil %}
    <div class="card border-{{o.al}}">
        <h4>{{o.name}} Öl (24h Vol-Check)</h4>
        Preis: <b>{{o.price}}</b> | RVOL: <span class="rvol-val">{{o.rvol}}</span><br>
        <span class="mini">Volumen: {{o.v_now}} (Heute) vs. {{o.v_yest}} (Gestern)</span>
    </div>
    {% endfor %}

    <h4>Markt-Monitor</h4>
    {% for a in assets %}
    <div class="card">
        <span class="chg-val" style="color:{{a.color}};">{{a.chg}}</span>
        <b>{{a.name}}</b><br>
        <span style="color:#aaa;">{{a.p}}</span>
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route("/")
def home():
    assets, ratio, oil = get_market_data()
    resp = make_response(render_template_string(HTML, assets=assets, ratio=ratio, oil=oil))
    resp.headers["Refresh"] = "45" # Update alle 45 Sekunden
    return resp

if __name__ == "__main__":
    app.run(debug=True)
