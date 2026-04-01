import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime

app = Flask(__name__)

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
            hist = ticker.history(period="10d") # Mehr Tage für stabilen RVOL
            if hist.empty: continue

            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # KUGELSICHERER RVOL (speziell für Silber/Kupfer)
            vols = hist['Volume'].replace(0, pd.NA).dropna()
            if len(vols) > 1:
                avg_vol = vols.iloc[:-1].mean()
                curr_vol = vols.iloc[-1]
                rvol = round(min(curr_vol / avg_vol, 15.0), 2) if avg_vol > 0 else 1.0
            else: rvol = 1.0

            # 7-TAGE-SPANNE
            low_7d, high_7d = hist['Low'].tail(7).min(), hist['High'].tail(7).max()
            range_pos = ((current_price - low_7d) / (high_7d - low_7d)) * 100 if (high_7d - low_7d) > 0 else 50

            # NEWS LOGIK
            news_items = []
            try:
                for n in ticker.news[:3]:
                    news_items.append({'title': n.get('title'), 'link': n.get('link')})
            except: pass

            results.append({
                'name': name, 'symbol': symbol, 'price': round(current_price, 2),
                'change': round(change_pct, 2), 'rvol': rvol, 
                'range_pos': round(range_pos, 0), 'news': news_items
            })
        except: continue
    return results, vix, eur_usd

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
            body { background: #121212; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
            .header { display: flex; justify-content: space-between; padding: 15px; background: #1e1e1e; border-radius: 10px; margin-bottom: 10px; border: 1px solid #333; }
            .card { background: #1e1e1e; padding: 15px; border-radius: 12px; margin-bottom: 8px; cursor: pointer; transition: 0.3s; border: 1px solid #222; }
            .alarm { border: 1px solid #ff5252; box-shadow: 0 0 10px rgba(255,82,82,0.2); animation: pulse 2s infinite; }
            @keyframes pulse { 0% { border-color: #ff5252; } 50% { border-color: #333; } 100% { border-color: #ff5252; } }
            .price-row { display: flex; justify-content: space-between; align-items: center; }
            .pos { color: #4caf50; } .neg { color: #ff5252; }
            .rvol-tag { font-size: 0.8em; padding: 2px 6px; background: #333; border-radius: 4px; }
            .range-bg { background: #222; height: 4px; border-radius: 2px; margin: 10px 0; }
            .range-bar { background: #81d4fa; height: 100%; border-radius: 2px; }
            .news-container { display: none; margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; animation: slideDown 0.3s; }
            @keyframes slideDown { from { opacity: 0; } to { opacity: 1; } }
            .news-link { color: #bbdefb; text-decoration: none; display: block; margin-bottom: 8px; font-size: 0.9em; line-height: 1.3; }
            .footer { font-size: 0.7em; color: #555; text-align: center; margin-top: 20px; }
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
        <div class="card {{ 'alarm' if item.rvol > 3 else '' }}" onclick="toggleNews('news-{{ loop.index }}')">
            <div class="price-row">
                <span style="font-size: 1.1em; font-weight: bold;">{{ item.name }}</span>
                <span style="font-size: 1.2em;">{{ item.price }}</span>
            </div>
            <div class="price-row" style="margin-top: 5px;">
                <span class="{{ 'pos' if item.change >= 0 else 'neg' }}">{{ item.change }}%</span>
                <span class="rvol-tag">RVOL: <b>{{ item.rvol }}</b></span>
            </div>
            <div class="range-bg"><div class="range-bar" style="width: {{ item.range_pos }}%;"></div></div>
            
            <div id="news-{{ loop.index }}" class="news-container">
                {% if item.news %}
                    {% for n in item.news %}
                        <a class="news-link" href="{{ n.link }}" target="_blank">● {{ n.title }}</a>
                    {% endfor %}
                {% else %}
                    <span style="font-size: 0.8em; color: #777;">Keine aktuellen News gefunden.</span>
                {% endif %}
            </div>
        </div>
        {% endfor %}

        <div class="footer">
            Privat-Radar ● Bettflucht Edition ● Keine Anlageberatung<br>
            {{ now.strftime('%d.%m. %H:%M:%S') }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=round(vix, 2), eur_usd=round(eur_usd, 4), now=datetime.datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
