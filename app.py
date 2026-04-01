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
        fx = yf.download("EURUSD=X", period="1d", interval="1m", progress=False)
        eur_usd = float(fx['Close'].iloc[-1]) if not fx.empty else 1.08
    except: eur_usd = 1.08
    try:
        vix_df = yf.download("^VIX", period="1d", interval="1m", progress=False)
        vix = float(vix_df['Close'].iloc[-1]) if not vix_df.empty else 15.0
    except: vix = 15.0

    for name, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            h = t.history(period="35d")
            if h.empty: continue
            curr = float(h['Close'].iloc[-1])
            prices[name] = curr
            change = ((curr - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            
            # RVOL 21-Tage Schnitt
            vols = h['Volume'].replace(0, pd.NA).dropna()
            if len(vols) > 5:
                avg = vols.iloc[-22:-1].mean()
                r_val = vols.iloc[-1] / avg if avg > 0 else 1.0
                rvol = round(min(r_val, 10.0), 2)
            else: rvol = 1.0

            low_7, high_7 = h['Low'].tail(7).min(), h['High'].tail(7).max()
            range_pos = ((curr - low_7) / (high_7 - low_7)) * 100 if (high_7 - low_7) > 0 else 50
            
            # NEWS FILTER (Nur wenn Titel vorhanden)
            news = []
            try:
                for n in t.news[:3]:
                    title = n.get('title')
                    if title and len(title) > 5: # Filtert "None" oder leere Titel aus
                        news.append({'title': title, 'link': n.get('link')})
            except: pass

            results.append({
                'name': name, 'price': format_de(curr, 2 if "EURUSD" not in symbol else 4),
                'change': format_de(change, 2), 'rvol': rvol, 'range_pos': round(range_pos, 0),
                'news': news, 'is_pos': change >= 0
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
            .header { display: flex; justify-content: space-between; padding: 12px; background: #111; border-radius: 10px; margin-bottom: 10px; border: 1px solid #222; font-size: 0.85em; }
            .card { background: #111; padding: 15px; border-radius: 12px; margin-bottom: 8px; border: 1px solid #222; cursor: pointer; }
            .alarm { border-color: #ff5252; box-shadow: 0 0 10px rgba(255,82,82,0.1); }
            .row { display: flex; justify-content: space-between; margin-bottom: 4px; }
            .pos { color: #4caf50; } .neg { color: #ff5252; }
            .rvol-tag { font-size: 0.7em; padding: 2px 5px; background: #222; border-radius: 4px; border: 1px solid #333; }
            .range-bg { background: #222; height: 3px; border-radius: 2px; margin: 10px 0; }
            .range-bar { background: #007aff; height: 100%; }
            .news-container { display: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; }
            .news-link { color: #81d4fa; text-decoration: none; display: block; margin-bottom: 10px; font-size: 0.8em; line-height:1.4; }
        </style>
        <script>
            function toggle(id) {
                var el = document.getElementById(id);
                if (el) { el.style.display = (el.style.display === 'block') ? 'none' : 'block'; }
            }
        </script>
    </head>
    <body>
        <div class="header">
            <span>VIX: <b>{{ vix }}</b></span>
            <span>G/S Ratio: <b>{{ gs_ratio }}</b></span>
            <span>€/$: <b>{{ eur_usd }}</b></span>
        </div>
        {% for item in data %}
        <div class="card {{ 'alarm' if item.rvol > 3.0 else '' }}" onclick="toggle('n-{{ loop.index }}')">
            <div class="row"><span style="color:#fff; font-weight:bold;">{{ item.name }}</span><span>{{ item.price }}</span></div>
            <div class="row"><span class="{{ 'pos' if item.is_pos else 'neg' }}">{{ item.change }}%</span><span class="rvol-tag">RVOL: {{ item.rvol }}</span></div>
            <div class="range-bg"><div class="range-bar" style="width: {{ item.range_pos }}%;"></div></div>
            
            {% if item.news %}
            <div id="n-{{ loop.index }}" class="news-container">
                {% for n in item.news %}
                    <a class="news-link" href="{{ n.link }}" target="_blank">● {{ n.title }}</a>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}
        <div style="text-align:center; font-size:0.6em; color:#444; margin-top:20px;">Stand: {{ now.strftime('%H:%M:%S') }}</div>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=vix, eur_usd=eur_usd, gs_ratio=gs_ratio, now=datetime.datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
