import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime

app = Flask(__name__)

TICKERS = {
    "Öl WTI": "CL=F", "Öl Brent": "BZ=F", "Gold": "GC=F",
    "Silber": "SI=F", "Kupfer": "HG=F", "S&P 500": "^GSPC",
    "DAX": "^GDAXI", "Nikkei 225": "^N225", "Hang Seng": "^HSI", "EUR/USD": "EURUSD=X"
}

def format_de(v, d=2):
    try: return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(v)

def get_market_data():
    results = []
    prices = {}
    
    # VIX - Fokus auf aktuellen Bereich um 25
    try:
        vix_data = yf.download("^VIX", period="1d", interval="1m", progress=False)
        vix = float(vix_data['Close'].iloc[-1]) if not vix_data.empty else 25.18
    except: vix = 25.0

    try:
        fx = yf.download("EURUSD=X", period="1d", interval="1m", progress=False)
        eur_usd = float(fx['Close'].iloc[-1]) if not fx.empty else 1.0850
    except: eur_usd = 1.0850

    for name, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="35d")
            if h.empty: continue
            
            # DIE MATHEMATIK: Aktuell vs. Gestern (Schlusskurs)
            curr = float(h['Close'].iloc[-1])
            prev = float(h['Close'].iloc[-2]) 
            change = ((curr - prev) / prev) * 100
            prices[name] = curr
            
            # RVOL Check (21-Tage Schnitt)
            vols = h['Volume'].replace(0, pd.NA).dropna()
            rvol = None
            if len(vols) > 5 and "EURUSD" not in symbol:
                avg = vols.iloc[-22:-1].mean()
                rvol = round(min(vols.iloc[-1] / avg, 10.0), 2) if avg > 0 else 1.0

            # AMPEL LOGIK (Insider-Scanner & Volatilität)
            ampel = "green"
            if (rvol and rvol > 2.5) or abs(change) > 2.1: ampel = "red"
            elif (rvol and rvol > 1.5) or abs(change) > 1.1: ampel = "yellow"

            # 7-TAGE-SPANNE (Balken-Position)
            low_7, high_7 = h['Low'].tail(7).min(), h['High'].tail(7).max()
            range_pos = ((curr - low_7) / (high_7 - low_7)) * 100 if (high_7 - low_7) > 0 else 50
            
            results.append({
                'name': name, 'symbol': symbol, 'ampel': ampel,
                'price': format_de(curr, 2 if "EURUSD" not in symbol else 4),
                'change': format_de(change, 2), 'rvol': rvol, 'range_pos': round(range_pos, 0),
                'is_pos': change >= 0
            })
        except: continue
    
    gs_ratio = format_de(prices.get("Gold", 0) / prices.get("Silber", 1), 2) if "Gold" in prices and "Silber" in prices else "N/A"
    return results, format_de(vix, 2), format_de(eur_usd, 4), gs_ratio

@app.route('/')
def index():
    data, vix, eur_usd, gs_ratio = get_market_data()
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
            .header { display: flex; justify-content: space-between; padding: 12px; background: #111; border-radius: 10px; margin-bottom: 12px; border: 1px solid #222; font-size: 0.85em; }
            .header a { color: #fff; text-decoration: none; font-weight: bold; }
            .card-link { text-decoration: none; color: inherit; display: block; }
            .card { background: #111; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-left: 6px solid #333; }
            
            /* Ampel-Farben */
            .border-red { border-left-color: #ff5252 !important; }
            .border-yellow { border-left-color: #ffd740 !important; }
            .border-green { border-left-color: #4caf50 !important; }
            
            .bg-red { background-color: #ff5252 !important; }
            .bg-yellow { background-color: #ffd740 !important; }
            .bg-green { background-color: #4caf50 !important; }
            
            /* Alarm-Blinken bei Rot */
            .card.border-red { animation: blink 2s infinite; }
            @keyframes blink { 0%, 100% { border-left-color: #ff5252; } 50% { border-left-color: #333; } }
            
            .row { display: flex; justify-content: space-between; margin-bottom: 4px; }
            .pos { color: #4caf50; } .neg { color: #ff5252; }
            .rvol-tag { font-size: 0.7em; padding: 2px 6px; background: #222; border-radius: 4px; border: 1px solid #333; color: #aaa; }
            
            /* Balken: Doppelte Stärke (6px) & Ampel-Farbe */
            .range-bg { background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; overflow: hidden; }
            .range-bar { height: 100%; transition: width 0.6s ease; }
            
            .footer { text-align: center; font-size: 0.65em; color: #444; margin-top: 25px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <a href="https://finance.yahoo.com/quote/%5EVIX" target="_blank">VIX: {{ vix }}</a>
            <span style="color: #aaa;">G/S: <b style="color: #fff;">{{ gs_ratio }}</b></span>
            <a href="https://finance.yahoo.com/quote/EURUSD=X" target="_blank">€/$: {{ eur_usd }}</a>
        </div>
        
        {% for item in data %}
        <a href="https://finance.yahoo.com/quote/{{ item.symbol }}" target="_blank" class="card-link">
            <div class="card border-{{ item.ampel }}">
                <div class="row"><span style="color:#fff; font-weight:bold;">{{ item.name }}</span><span style="font-size: 1.1em; font-weight: bold;">{{ item.price }}</span></div>
                <div class="row">
                    <span class="{{ 'pos' if item.is_pos else 'neg' }}" style="font-weight: bold;">{{ item.change }}%</span>
                    {% if item.rvol %}<span class="rvol-tag">RVOL: {{ item.rvol }}</span>{% endif %}
                </div>
                <div class="range-bg">
                    <div class="range-bar bg-{{ item.ampel }}" style="width: {{ item.range_pos }}%;"></div>
                </div>
            </div>
        </a>
        {% endfor %}
        
        <div class="footer">
            INSIDER-RADAR AKTIV ● {{ now.strftime('%H:%M:%S') }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=vix, eur_usd=eur_usd, gs_ratio=gs_ratio, now=datetime.datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
