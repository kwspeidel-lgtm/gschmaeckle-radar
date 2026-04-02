import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
from datetime import datetime, timedelta

app = Flask(__name__)

TICKERS = {
    "Bitcoin": "BTC-USD",
    "Öl WTI": "CL=F", "Öl Brent": "BZ=F",
    "Gold": "GC=F", "Silber": "SI=F", "Kupfer": "HG=F",
    "S&P 500": "^GSPC", "DAX": "^GDAXI", "Nikkei 225": "^N225",
    "Hang Seng": "^HSI", "EUR/USD": "EURUSD=X"
}

def format_de(v, d=2):
    if v is None: return "N/A"
    try:
        return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(v)

def calc_rvol_safe(symbol, name):
    if name == "Kupfer": return None
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="60d")
        if len(hist) < 30: return None
        vol_today, vol_median = hist['Volume'].iloc[-1], hist['Volume'].iloc[:-1].median()
        if vol_median == 0 or pd.isna(vol_today): return None
        rvol_raw = vol_today / vol_median
        if name in ["Gold", "Silber"] and rvol_raw > 5.555: return 5.555
        return round(rvol_raw, 2)
    except: return None

def get_market_data():
    results = []
    prices = {}
    
    # TURBO-FETCH: Alle Ticker gleichzeitig laden (1m Intervall für Frische)
    all_syms = list(TICKERS.values()) + ["^VIX"]
    df = yf.download(all_syms, period="1d", interval="1m", progress=False)

    # VIX Spezial-Logik
    try:
        vix_curr = df['Close']['^VIX'].iloc[-1]
        vix_prev = yf.Ticker("^VIX").fast_info['previous_close']
        vix_change = ((vix_curr - vix_prev) / vix_prev) * 100
        vix_val_col = "#ff5252" if vix_curr >= 30 else ("#ffd740" if vix_curr >= 25 else "#e0e0e0")
        vix_pct_col = "#ff5252" if vix_change > 0 else "#4caf50"
    except:
        vix_curr, vix_change, vix_val_col, vix_pct_col = 26.66, 0.0, "#ffd740", "#ff5252"

    for name, symbol in TICKERS.items():
        try:
            curr = df['Close'][symbol].iloc[-1]
            prev = yf.Ticker(symbol).fast_info['previous_close']
            change = ((curr - prev) / prev) * 100
            prices[name] = curr
            
            rvol = calc_rvol_safe(symbol, name) if name in ["Öl WTI", "Öl Brent", "Gold", "Silber"] else None
            is_alert = rvol >= 3.0 if rvol else False
            ampel = "neutral"
            if rvol:
                if rvol >= 3.0: ampel = "red" if change < 0 else "green"
                elif rvol >= 1.2: ampel = "green" if change > 0 else "red"
                elif rvol < 0.8: ampel = "yellow"

            # 7-Tage Range für den Balken
            h_7d = yf.Ticker(symbol).history(period="7d")
            l7, h7 = h_7d['Low'].min(), h_7d['High'].max()
            range_pos = ((curr - l7) / (h7 - l7)) * 100 if (h7 - l7) > 0 else 50

            results.append({
                'name': name, 'symbol': symbol, 'ampel': ampel, 'alert': is_alert,
                'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)),
                'change': format_de(change, 2), 'rvol': rvol, 'range_pos': round(range_pos, 0), 'is_pos': change >= 0,
                'url': f"https://finance.yahoo.com/quote/{symbol}"
            })
        except: continue

    # Gold-Silber-Ratio Farbe (Gold wenn Gold stärker, Silber wenn Silber stärker)
    gs_val = prices.get("Gold", 0) / prices.get("Silber", 1) if "Gold" in prices and "Silber" in prices else 0
    gs_color = "#ffd700" 
    try:
        g_c = (prices["Gold"] / yf.Ticker("GC=F").fast_info['previous_close']) - 1
        s_c = (prices["Silber"] / yf.Ticker("SI=F").fast_info['previous_close']) - 1
        if s_c > g_c: gs_color = "#c0c0c0" 
    except: pass

    berlin_time = datetime.now() + timedelta(hours=2)
    vix_data = {'val': format_de(vix_curr, 2), 'pct': format_de(vix_change, 2), 'v_col': vix_val_col, 'p_col': vix_pct_col, 'url': "https://finance.yahoo.com/quote/^VIX"}
    
    return results, vix_data, format_de(gs_val, 2), gs_color, berlin_time

@app.route('/')
def index():
    data, vix, gs_str, gs_color, now_time = get_market_data()
    ki_block = f"RAW_DATA|VIX:{vix['val']}|GS:{gs_str}"
    for d in data:
        rv = d['rvol'] if d['rvol'] else "0"
        ki_block += f"|{d['name']}:{d['price']}:{d['change']}%:RV{rv}"

    html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body { background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
    .header { display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-weight: bold; }
    .btn { background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; height: 55px; font-size: 1.1em; }
    .card { background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }
    .insider-alert { border-left-color: #ff5252 !important; animation: pulse 1.5s infinite; background: #1a0505; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255,82,82,0.4); } 70% { box-shadow: 0 0 0 12px rgba(255,82,82,0); } 100% { box-shadow: 0 0 0 0 rgba(255,82,82,0); } }
    .border-red { border-left-color: #ff5252; } .border-yellow { border-left-color: #ffd740; } .border-green { border-left-color: #4caf50; }
    .row { display: flex; justify-content: space-between; align-items: center; }
    a { color: inherit; text-decoration: none; display: block; width: 100%; }
    .price-text { font-weight: 900; font-size: 1.2em; text-align: right; }
    .text-green { color: #4caf50; } .text-red { color: #ff5252; }
    .rvol-tag { font-size: 0.85em; font-weight: 800; padding: 4px 8px; background: #222; border-radius: 6px; }
    .rvol-high { background: #e67e22; color: #fff; }
    .range-bg { background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }
    .range-bar { height: 100%; border-radius: 3px; }
    .bg-red { background-color: #ff5252; } .bg-yellow { background-color: #ffd740; } .bg-green { background-color: #4caf50; }
    .footer { text-align: center; font-size: 0.8em; color: #555; margin-top: 20px; font-weight: bold; }
    </style></head><body>
    <div class="header">
        <a href="{{ vix.url }}" target="_blank">VIX: <b style="color:{{ vix.v_col }};">{{ vix.val }}</b> <span style="font-size:0.8em; color:{{ vix.p_col }};">({{ vix.pct }}%)</span></a>
        <span>G/S Ratio: <b style="color:{{ gs_color }};">{{ gs_str }}</b></span>
    </div>
    <button class="btn" onclick="copyKI()">SHORTCUT 2 ANALYSE KOPIEREN 🚀</button>
    {% for item in data %}
    <div class="card {{ 'insider-alert' if item.alert else 'border-' + item.ampel }}">
        <a href="{{ item.url }}" target="_blank">
            <div class="row"><b>{{ item.name }}</b><span class="price-text {{ 'text-green' if item.is_pos else 'text-red' }}">{{ item.price }}</span></div>
            <div class="row" style="margin-top:8px;">
                <span style="font-weight:800; font-size:1.05em; color: {{ '#4caf50' if item.is_pos else '#ff5252' }};">{{ item.change }}%</span>
                {% if item.rvol %}<span class="rvol-tag {{ 'rvol-high' if item.rvol >= 3.0 }}">RVOL: {{ item.rvol }}</span>{% endif %}
            </div>
            <div class="range-bg"><div class="range-bar bg-{{ item.ampel }}" style="width:{{ item.range_pos }}%;"></div></div>
        </a>
    </div>
    {% endfor %}
    <div class="footer">RADAR AKTIV ● BERLIN: {{ now.strftime('%H:%M:%S') }}</div>
    <script>function copyKI(){navigator.clipboard.writeText(`{{ ki_block }}`).then(()=>alert("DATEN KOPIERT!"));}</script>
    </body></html>"""
    return render_template_string(html, data=data, vix=vix, gs_str=gs_str, gs_color=gs_color, now=now_time)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
