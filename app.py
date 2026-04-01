import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime
import re

app = Flask(__name__)

TICKERS = {
    "Öl WTI": "CL=F",
    "Öl Brent": "BZ=F",
    "Gold": "GC=F",
    "Silber": "SI=F",
    "Kupfer": "HG=F",
    "S&P 500": "^GSPC",
    "DAX": "^GDAXI",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "EUR/USD": "EURUSD=X"
}

def format_de(value, decimals=2):
    try:
        return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return str(value)

def get_market_data():
    results = []
    # FX & VIX Abruf
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
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            if hist.empty: continue

            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # RVOL Check
            vols = hist['Volume'].replace(0, pd.NA).dropna()
            avg_vol = vols.iloc[:-1].mean() if len(vols) > 1 else 1
            rvol = round(min(vols.iloc[-1] / avg_vol, 15.0), 2) if avg_vol > 0 else 1.0

            # 7-Tage-Spanne
            low_7, high_7 = hist['Low'].tail(7).min(), hist['High'].tail(7).max()
            range_pos = ((current_price - low_7) / (high_7 - low_7)) * 100 if (high_7 - low_7) > 0 else 50

            # STABILERER NEWS-ABRUF
            news_items = []
            try:
                # Wir holen die News direkt und prüfen die Titel-Existenz
                raw_news = ticker.news
                if raw_news:
                    for n in raw_news[:3]:
                        title = n.get('title') or n.get('headline')
                        link = n.get('link') or n.get('url')
                        if title and title != "None":
                            news_items.append({'title': title, 'link': link})
            except: pass

            results.append({
                'name': name, 'symbol': symbol, 
                'price': format_de(current_price, 2 if "EURUSD" not in symbol else 4),
                'change': format_de(change_pct, 2), 
                'rvol': format_de(rvol, 2), 
                'range_pos': round(range_pos, 0), 
                'news': news_items,
                'is_pos': change_pct >= 0
            })
        except: continue
    return results, format_de(vix, 2), format_de(eur_usd, 4)

@app.route('/')
def index():
    data, vix, eur_usd = get_market_data()
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { background: #000; color: #e0e0e0; font-family: -apple-system, sans-serif; margin: 10px; }
            .header { display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-size: 0.9em; }
            .card { background: #111; padding: 16px; border-radius: 14px; margin-bottom: 10px; cursor: pointer; border: 1px solid #222; }
            .alarm { border: 1px solid #ff5252; box-shadow: 0 0 15px rgba(255,82,82,0.15); animation: pulse 2s infinite; }
            @keyframes pulse { 0%, 100% { border-color: #ff5252; } 50% { border-color: #222; } }
            .row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
            .pos { color: #4caf50; } .neg { color: #ff5252; }
            .rvol-tag { font-size: 0.75em; padding: 3px 7px; background: #222; border-radius: 6px; color: #aaa; }
            .range-bg { background: #222; height: 4px; border-radius: 2px; margin: 12px 0; overflow: hidden; }
            .range-bar { background: #007aff; height: 100%; }
            .news-container { display: none; margin-top: 12px; padding-top: 12px; border-top: 1px solid #222; }
            .news-link { color: #81d4fa; text-decoration: none; display: block; margin-bottom: 12px; font-size: 0.85em; line-height: 1.4; }
            .footer { font-size: 0.65em; color: #444; text-align: center; margin-top: 30px; line-height: 1.5; }
        </style>
        <script>
            function toggleNews(id) {
                var x = document.getElementById(id);
                x.style.display = (x.style.display === "block") ? "none" : "block";
            }
        </script>
    </head>
    <body>
        <div class="header">
            <span>VIX: <b>{{ vix }}</b></span>
            <span>€/$: <b>{{ eur_usd }}</b></span>
        </div>

        {% for item in data %}
        <div class="card {{ 'alarm' if item.rvol|replace('.','')|replace(',','.')|float > 3.0 else '' }}" onclick="toggleNews('news-{{ loop.index }}')">
            <div class="row">
                <span style="font-weight: 600; color: #fff;">{{ item.name }}</span>
                <span style="font-size: 1.1em; font-weight: 700;">{{ item.price }}</span>
            </div>
            <div class="row">
                <span class="{{ 'pos' if item.is_pos else 'neg' }}" style="font-weight: 500;">{{ item.change }}%</span>
                <span class="rvol-tag">RVOL: {{ item.rvol }}</span>
            </div>
            <div class="range-bg"><div class="range-bar" style="width: {{ item.range_pos }}%;"></div></div>
            
            <div id="news-{{ loop.index }}" class="news-container" style="display: {{ 'block' if item.news else 'none' }};">
                {% if item.news %}
                    {% for n in item.news %}
                        <a class="news-link" href="{{ n.link }}" target="_blank">→ {{ n.title }}</a>
                    {% endfor %}
                {% endif %}
            </div>
        </div>
        {% endfor %}

        <div class="footer">
            GESCHMÄCKLE-RADAR ● BEOBACHTUNG ● {{ now.strftime('%H:%M:%S') }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=vix, eur_usd=eur_usd, now=datetime.datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
