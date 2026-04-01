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
    
    try:
        vix_t = yf.Ticker("^VIX")
        vix_h = vix_t.history(period="2d")
        vix = float(vix_h['Close'].iloc[-1]) if not vix_h.empty else 25.0
    except: vix = 25.0

    for name, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="35d")
            if len(h) < 2: continue
            
            valid_h = h.dropna(subset=['Close'])
            curr = float(valid_h['Close'].iloc[-1])
            prev = float(valid_h['Close'].iloc[-2]) 
            change = ((curr - prev) / prev) * 100
            prices[name] = curr
            
            vols = valid_h['Volume'].replace(0, pd.NA).dropna()
            rvol = None
            if len(vols) > 5 and "EURUSD" not in symbol:
                avg = vols.iloc[-22:-1].mean()
                rvol = round(min(vols.iloc[-1] / avg, 10.0), 2) if avg > 0 else 1.0

            ampel = "green"
            if (rvol and rvol > 2.5) or abs(change) > 2.1: ampel = "red"
            elif (rvol and rvol > 1.5) or abs(change) > 1.1: ampel = "yellow"

            # FIX: Hier war der Fehler (doppeltes high_7 entfernt)
            low_7 = valid_h['Low'].tail(7).min()
            high_7 = valid_h['High'].tail(7).max()
            range_pos = ((curr - low_7) / (high_7 - low_7)) * 100 if (high_7 - low_7) > 0 else 50
            
            results.append({
                'name': name, 'symbol': symbol, 'ampel': ampel,
                'price': format_de(curr, 2 if "EURUSD" not in symbol else 4),
                'change': format_de(change, 2), 'rvol': rvol, 'range_pos': round(range_pos, 0),
                'is_pos': change >= 0
            })
        except: continue
    
    gs_ratio = format_de(prices.get("Gold", 0) / prices.get("Silber", 1), 2) if "Gold" in prices and "Silber" in prices else "N/A"
    return results, format_de(vix, 2), gs_ratio

@app.route('/')
def index():
    data, vix, gs_ratio = get_market_data()
    ki_block = f"RAW_DATA|VIX:{vix}|GS:{gs_ratio}"
    for d in data:
        rv = d['rvol'] if d['rvol'] else "0"
        ki_block += f"|{d['name']}:{d['price']}:{d['change']}%:RV{rv}"

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
            .header { display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; }
            .gemini-btn { background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; font-size: 1.1em; }
            .card-link { text-decoration: none; color: inherit; display: block; }
            .card { background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }
            .border-red { border-left-color: #ff5252 !important; animation: blink 2s infinite; }
            .border-yellow { border-left-color: #ffd740 !important; }
            .border-green { border-left-color: #4caf50 !important; }
            @keyframes blink { 0%, 100% { border-left-color: #ff5252; } 50% { border-left-color: #222; } }
            .row { display: flex; justify-content: space-between; align-items: center; }
            .rvol-tag { font-size: 0.85em; font-weight: 800; padding: 4px 8px; background: #333; border-radius: 6px; color: #fff; border: 1px solid #555; }
            .range-bg { background: #1a1a1a; height: 8px; border-radius: 4px; margin: 12px 0; overflow: hidden; }
            .range-bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
            .bg-red { background-color: #ff5252; } .bg-yellow { background-color: #ffd740; } .bg-green { background-color: #4caf50; }
            .footer { text-align: center; font-size: 0.7em; color: #444; margin-top: 20px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <span>VIX: <b>{{ vix }}</b></span>
            <span>G/S: <b>{{ gs_ratio }}</b></span>
        </div>
        
        <button class="gemini-btn" onclick="copyKI()">SHORTCUT 2 ANALYSE 🚀</button>

        {% for item in data %}
        <a href="https://finance.yahoo.com/quote/{{ item.symbol }}" target="_blank" class="card-link">
            <div class="card border-{{ item.ampel }}">
                <div class="row"><span style="font-weight:bold; color:#fff;">{{ item.name }}</span><span style="font-weight:900; font-size:1.1em;">{{ item.price }}</span></div>
                <div class="row" style="margin-top:8px;">
                    <span style="font-weight:800; font-size:1.05em; color: {{ '#4caf50' if item.is_pos else '#ff5252' }};">{{ item.change }}%</span>
                    {% if item.rvol %}<span class="rvol-tag">RVOL: {{ item.rvol }}</span>{% endif %}
                </div>
                <div class="range-bg"><div class="range-bar bg-{{ item.ampel }}" style="width:{{ item.range_pos }}%;"></div></div>
            </div>
        </a>
        {% endfor %}
        
        <div class="footer">RADAR AKTIV ● {{ now.strftime('%H:%M:%S') }}</div>

        <script>
            function copyKI() {
                const text = `{{ ki_block }}`;
                navigator.clipboard.writeText(text).then(() => {
                    alert("KI-DATEN KOPIERT! Jetzt in Gemini einfügen.");
                }).catch(err => {
                    alert("Kopierfehler.");
                });
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=vix, gs_ratio=gs_ratio, ki_block=ki_block, now=datetime.datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
