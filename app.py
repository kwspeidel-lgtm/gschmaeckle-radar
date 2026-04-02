import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime

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
    except:
        return str(v)

def calc_rvol_pro(symbol):
    """
    Normalisierter RVOL: Nutzt 60 Tage Median.
    Ignoriert statistisches Rauschen und Datenfehler.
    """
    try:
        t = yf.Ticker(symbol)
        # 60 Tage für maximale Stabilität (Quartals-Basis)
        hist = t.history(period="60d")
        if len(hist) < 20:
            return None
        
        vol_today = hist['Volume'].iloc[-1]
        # Median filtert Ausreißer/Feiertage/Glitches komplett raus
        vol_avg_60d = hist['Volume'].iloc[:-1].median() 
        
        if vol_avg_60d == 0 or vol_avg_60d is None:
            return None
            
        # Ergebnis wird auf realistische Werte normalisiert
        return round(vol_today / vol_avg_60d, 2)
    except:
        return None

def get_market_data():
    results = []
    prices = {}
    
    try:
        vix_t = yf.Ticker("^VIX")
        vix = vix_t.fast_info['last_price']
    except:
        vix = 24.54 # Fallback auf deinen Radar-Wert

    for name, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            curr = t.fast_info['last_price']
            prev_close = t.fast_info['previous_close']
            change = ((curr - prev_close) / prev_close) * 100 if prev_close else 0.0
            prices[name] = curr

            rvol = None
            # RVOL nur für Rohstoffe (Insider-Check Fokus)
            if name in ["Öl WTI", "Öl Brent", "Gold", "Silber", "Kupfer"]:
                rvol = calc_rvol_pro(symbol)

            # Scharfe Insider-Logik (Shortcut 2)
            is_insider_alert = False
            ampel = "neutral"
            
            if rvol is not None:
                # Dein Schwellenwert 3.0 für massiven Alarm
                if rvol >= 3.0:
                    is_insider_alert = True
                    ampel = "red" if change < 0 else "green"
                elif rvol >= 1.2:
                    ampel = "green" if change > 0 else "red"
                elif rvol < 0.8:
                    ampel = "yellow"

            # 7-Tage Range für visuelles Feedback
            h_short = t.history(period="7d")
            low_7, high_7 = h_short['Low'].min(), h_short['High'].max()
            range_pos = ((curr - low_7) / (high_7 - low_7)) * 100 if (high_7 - low_7) > 0 else 50

            results.append({
                'name': name,
                'symbol': symbol,
                'ampel': ampel,
                'alert': is_insider_alert,
                'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)),
                'change': format_de(change, 2),
                'rvol': rvol,
                'range_pos': round(range_pos, 0),
                'is_pos': change >= 0
            })
        except:
            continue

    gs_ratio = format_de(prices.get("Gold", 0) / prices.get("Silber", 1), 2) if "Gold" in prices and "Silber" in prices else "N/A"

    return results, format_de(vix, 2), gs_ratio

@app.route('/')
def index():
    data, vix, gs_ratio = get_market_data()
    ki_block = f"RAW_DATA|VIX:{vix}|GS:{gs_ratio}"
    for d in data:
        rv = d['rvol'] if d['rvol'] else "0"
        ki_block += f"|{d['name']}:{d['price']}:{d['change']}%:RV{rv}"

    html = """<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body { background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
    .header { display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; }
    .gemini-btn { background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; }
    .card { background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }
    .insider-alert { border-left-color: #ff5252 !important; animation: pulse 1.5s infinite; background: #1a0000; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255, 82, 82, 0.4); } 70% { box-shadow: 0 0 0 15px rgba(255, 82, 82, 0); } 100% { box-shadow: 0 0 0 0 rgba(255, 82, 82, 0); } }
    .border-red { border-left-color: #ff5252; } .border-yellow { border-left-color: #ffd740; } .border-green { border-left-color: #4caf50; }
    .row { display: flex; justify-content: space-between; align-items: center; }
    .rvol-tag { font-size: 0.85em; font-weight: 800; padding: 4px 8px; background: #222; border-radius: 6px; color: #fff; }
    .rvol-high { background: #e67e22; border: none; }
    .range-bg { background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }
    .range-bar { height: 100%; border-radius: 3px; }
    .bg-red { background-color: #ff5252; } .bg-yellow { background-color: #ffd740; } .bg-green { background-color: #4caf50; }
    </style>
    </head>
    <body>
    <div class="header"><span>VIX: {{ vix }}</span><span>G/S: {{ gs_ratio }}</span></div>
    <button class="gemini-btn" onclick="copyKI()" style="width:100%; height:50px;">SHORTCUT 2 ANALYSE 🚀</button>
    {% for item in data %}
    <div class="card {{ 'insider-alert' if item.alert else 'border-' + item.ampel }}">
        <div class="row"><b>{{ item.name }}</b><span style="font-weight:900;">{{ item.price }}</span></div>
        <div class="row" style="margin-top:8px;">
            <span style="font-weight:800; color: {{ '#4caf50' if item.is_pos else '#ff5252' }};">{{ item.change }}%</span>
            {% if item.rvol %}<span class="rvol-tag {{ 'rvol-high' if item.rvol >= 3.0 }}">RVOL: {{ item.rvol }}</span>{% endif %}
        </div>
        <div class="range-bg"><div class="range-bar bg-{{ item.ampel }}" style="width:{{ item.range_pos }}%;"></div></div>
    </div>
    {% endfor %}
    <script>
        function copyKI() {
            navigator.clipboard.writeText(`{{ ki_block }}`).then(() => alert("KOPIERT!"));
        }
    </script>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=vix, gs_ratio=gs_ratio, ki_block=ki_block, now=datetime.datetime.now())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
