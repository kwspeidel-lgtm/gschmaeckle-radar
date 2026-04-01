import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime

app = Flask(__name__)

# DEINE TICKER-LISTE
TICKERS = {
    "Öl (WTI)": "CL=F",
    "Gold": "GC=F",
    "Silber": "SI=F",
    "Kupfer": "HG=F",
    "S&P 500": "^GSPC",
    "DAX": "^GDAXI",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "EUR/USD": "EURUSD=X"
}

def get_market_data():
    results = []
    
    # 1. Gemeinsamer Abruf für Header-Daten (VIX, FX, Gold/Silber Ratio)
    all_symbols = list(TICKERS.values()) + ["^VIX", "EURUSD=X"]
    try:
        data_all = yf.download(all_symbols, period="2d", interval="1d", progress=False)
        current_prices = data_all['Close'].iloc[-1]
        
        eur_usd = round(float(current_prices.get('EURUSD=X', 1.0820)), 4)
        vix = round(float(current_prices.get('^VIX', 15.50)), 2)
        
        # Gold-Silber-Ratio Berechnung
        gold_p = float(current_prices.get('GC=F', 0))
        silver_p = float(current_prices.get('SI=F', 0))
        gs_ratio = round(gold_p / silver_p, 2) if silver_p > 0 else "N/A"
    except:
        eur_usd, vix, gs_ratio = 1.0820, 15.50, "N/A"

    # 2. Details pro Ticker (RVOL, Change, News)
    for name, symbol in TICKERS.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="7d")
            if hist.empty: continue

            price = hist['Close'].iloc[-1]
            change = ((price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            
            avg_vol = hist['Volume'].iloc[:-1].mean()
            rvol = round(hist['Volume'].iloc[-1] / avg_vol, 2) if avg_vol > 0 else 0

            low_7d, high_7d = hist['Low'].min(), hist['High'].max()
            range_pos = ((price - low_7d) / (high_7d - low_7d)) * 100 if (high_7d - low_7d) > 0 else 50

            # News-Fix: Keine "None" Anzeigen
            news_list = []
            try:
                for n in t.news[:3]:
                    title = n.get('title')
                    link = n.get('link')
                    if title and link:
                        news_list.append({'title': title, 'link': link})
            except: pass

            results.append({
                'name': name, 'price': round(price, 2), 'change': round(change, 2),
                'rvol': rvol, 'range_pos': round(range_pos, 0), 'news': news_list
            })
        except: continue
        
    return results, vix, eur_usd, gs_ratio

@app.route('/')
def index():
    data, vix, eur_usd, gs_ratio = get_market_data()
    now = datetime.datetime.now()
    
    html = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gschmäckle-Radar</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: sans-serif; margin: 5px; }
            .header { display: flex; justify-content: space-between; padding: 12px; background: #1e1e1e; border-radius: 8px; margin-bottom: 10px; border-bottom: 2px solid #444; font-size: 0.9em; }
            .card { background: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid #444; position: relative; }
            .alarm { border-left-color: #ff5252; box-shadow: 0 0 15px rgba(255,82,82,0.2); animation: pulse 2s infinite; }
            @keyframes pulse { 0% { border-left-width: 4px; } 50% { border-left-width: 8px; } 100% { border-left-width: 4px; } }
            .pos { color: #4caf50; } .neg { color: #ff5252; }
            .range-bg { background: #333; height: 5px; border-radius: 3px; margin: 10px 0; overflow: hidden; }
            .range-bar { background: #03a9f4; height: 100%; border-radius: 3px; }
            .news-link { color: #81d4fa; text-decoration: none; display: block; font-size: 0.82em; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; border-left: 2px solid #03a9f4; padding-left: 5px; }
            .footer { text-align: center; font-size: 0.7em; color: #555; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="header">
            <span>VIX: <b>{{ vix }}</b></span>
            <span>G/S Ratio: <b style="color:#ffb74d">{{ gs_ratio }}</b></span>
            <span>EUR/USD: <b>{{ eur_usd }}</b></span>
        </div>

        {% for item in data %}
        <div class="card {{ 'alarm' if item.rvol > 3 else '' }}">
            <div style="display:flex; justify-content:space-between; font-weight:bold; font-size: 1.1em;">
                <span>{{ item.name }}</span><span>{{ item.price }}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.95em; margin-top:5px;">
                <span class="{{ 'pos' if item.change >= 0 else 'neg' }}">{{ '+' if item.change > 0 }}{{ item.change }}%</span>
                <span>RVOL: <b style="{{ 'color:#ff5252; font-size:1.1em;' if item.rvol > 3 else '' }}">{{ item.rvol }}</b></span>
            </div>
            
            <div class="range-bg"><div class="range-bar" style="width: {{ item.range_pos }}%;"></div></div>

            {% for n in item.news %}
                <a class="news-link" href="{{ n.link }}" target="_blank">🗞️ {{ n.title }}</a>
            {% endfor %}
        </div>
        {% endfor %}

        <div class="footer">
            Gschmäckle-Radar Live | Stand: {{ now.strftime('%H:%M:%S') }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=vix, eur_usd=eur_usd, gs_ratio=gs_ratio, now=now)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
