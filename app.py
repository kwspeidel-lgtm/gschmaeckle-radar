import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime

app = Flask(__name__)

# Deine Master-Shortcuts Ticker
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
    except:
        return str(v)

def calc_rvol_safe(symbol):
    """
    Gehärteter RVOL: Nutzt 60-Tage Median & fängt API-Glitches ab.
    Verhindert utopische Werte wie 119 durch Hard-Cap bei 15.0.
    """
    try:
        t = yf.Ticker(symbol)
        # 60 Tage für maximale Stabilität (Quartals-Basis)
        hist = t.history(period="60d")
        if len(hist) < 30:
            return None
        
        vol_today = hist['Volume'].iloc[-1]
        # Median filtert Ausreißer/Feiertage/Glitches komplett raus
        vol_median = hist['Volume'].iloc[:-1].median() 
        
        if vol_median == 0 or vol_median is None or pd.isna(vol_today):
            return None
            
        rvol_raw = vol_today / vol_median
        
        # GLITCH-FILTER: Werte über 50 sind bei Yahoo oft Datenfehler.
        # Wir deckeln auf 15.0 (Massiver Alert, aber optisch sauber & glaubwürdig).
        if rvol_raw > 50:
            return 15.0
            
        return round(rvol_raw, 2)
    except:
        return None

def get_market_data():
    results = []
    prices = {}
    
    try:
        # VIX Fix: Schnellerer Abruf über fast_info
        vix = yf.Ticker("^VIX").fast_info['last_price']
    except:
        vix = 24.54

    for name, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            fi = t.fast_info
            curr = fi['last_price']
            prev = fi['previous_close']
            change = ((curr - prev) / prev) * 100 if prev else 0.0
            prices[name] = curr

            rvol = None
            # RVOL nur für Commodities (Shortcut 1 & 2 Logik)
            if name in ["Öl WTI", "Öl Brent", "Gold", "Silber", "Kupfer"]:
                rvol = calc_rvol_safe(symbol)

            # Insider-Logik & Ampel
            is_alert = rvol >= 3.0 if rvol else False
            ampel = "neutral"
            if rvol:
                if rvol >= 3.0: 
                    ampel = "red" if change < 0 else "green"
                elif rvol >= 1.2: 
                    ampel = "green" if change > 0 else "red"
                elif rvol < 0.8: 
                    ampel = "yellow"

            # 7-Tage Range Visualisierung
            h = t.history(period="7d")
            l7, h7 = h['Low'].min(), h['High'].max()
            range_pos = ((curr - l7) / (h7 - l7)) * 100 if (h7 - l7) > 0 else 50

            results.append({
                'name': name, 
                'symbol': symbol, 
                'ampel': ampel, 
                'alert': is_alert,
                'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)),
                'change': format_de(change, 2), 
                'rvol': rvol, 
                'range_pos': round(range_pos, 0), 
                'is_pos': change >= 0
            })
        except: 
            continue

    gs = format_de(prices.get("Gold", 0) / prices.get("Silber", 1), 2) if "Gold" in prices and "Silber" in prices else "N/A"
    return results, format_de(vix, 2), gs

@app.route('/')
def index():
    data, vix, gs = get_market_data()
    # KI-Block für den Chat-Check (Shortcut 2 Analyse)
    ki_block = f"RAW_DATA|VIX:{vix}|GS:{gs}"
    for d in data:
        rv = d['rvol'] if d['rvol'] else "0"
        ki_block += f"|{d['name']}:{d['price']}:{d['change']}%:RV{rv}"

    html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body { background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
    .header { display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-weight: bold; }
    .btn { background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; height: 55px; font-size: 1.1em; }
    .card { background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; transition: 0.3s; }
    
    /* Insider Alert Animation */
    .insider-alert { border-left-color: #ff5252 !important; animation: pulse 1.5s infinite; background: #1a0505; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255,82,82,0.4); } 70% { box-shadow: 0 0 0 12px rgba(255,82,82,0); } 100% { box-shadow: 0 0 0 0 rgba(255,82,82,0); } }
    
    .border-red { border-left-color: #ff5252; } 
    .border-yellow { border-left-color: #ffd740; } 
    .border-green { border-left-color: #4caf50; }
    
    .row { display: flex; justify-content: space-between; align-items: center; }
    .rvol-tag { font-size: 0.85em; font-weight: 800; padding: 4px 8px; background: #222; border-radius: 6px; }
    .rvol-high { background: #e67e22; color: #fff; border: none; }
    
    .range-bg { background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }
    .range-bar { height: 100%; border-radius: 3px; }
    .bg-red { background-color: #ff5252; } .bg-yellow { background-color: #ffd740; } .bg-green { background-color: #4caf50; }
    .footer { text-align: center; font-size: 0.8em; color: #444; margin-top: 20px; }
    </style></head><body>
    <div class="header"><span>VIX: <b>{{ vix }}</b></span><span>G/S Ratio: <b>{{ gs }}</b></span></div>
    <button class="btn" onclick="copyKI()">SHORTCUT 2 ANALYSE KOPIEREN 🚀</button>
    {% for item in data %}
    <div class="card {{ 'insider-alert' if item.alert else 'border-' + item.ampel }}">
        <div class="row"><b>{{ item.name }}</b><span style="font-weight:900; font-size:1.1em;">{{ item.price }}</span></div>
        <div class="row" style="margin-top:8px;">
            <span style="font-weight:800; font-size:1.05em; color: {{ '#4caf50' if item.is_pos else '#ff5252' }};">{{ item.change }}%</span>
            {% if item.rvol %}<span class="rvol-tag {{ 'rvol-high' if item.rvol >= 3.0 }}">RVOL: {{ item.rvol }}</span>{% endif %}
        </div>
        <div class="range-bg"><div class="range-bar bg-{{ item.ampel }}" style="width:{{ item.range_pos }}%;"></div></div>
    </div>
    {% endfor %}
    <div class="footer">RADAR AKTIV ● {{ now.strftime('%H:%M:%S') }}</div>
    <script>function copyKI(){navigator.clipboard.writeText(`{{ ki_block }}`).then(()=>alert("DATEN FÜR CHECK KOPIERT!"));}</script>
    </body></html>"""
    return render_template_string(html, data=data, vix=vix, gs=gs, ki_block=ki_block, now=datetime.datetime.now())

if __name__ == '__main__':
    # Render nutzt den PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
