import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
import datetime

app = Flask(__name__)

# DEINE TICKER-LISTE (Anpassbar)
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
    
    # 1. EUR/USD & VIX (Sicherheits-Check)
    try:
        fx = yf.download("EURUSD=X", period="1d", interval="1m", progress=False)
        eur_usd = float(fx['Close'].iloc[-1]) if not fx.empty else 1.08
    except:
        eur_usd = 1.08

    try:
        vix_df = yf.download("^VIX", period="1d", interval="1m", progress=False)
        vix = float(vix_df['Close'].iloc[-1]) if not vix_df.empty else 15.0
    except:
        vix = 15.0

    # 2. Daten für jeden Ticker holen
    for name, symbol in TICKERS.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="7d")
            
            if hist.empty:
                continue

            current_price = float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close) * 100
            
            # RVOL Logik (Relatives Volumen)
            avg_vol = hist['Volume'].iloc[:-1].mean()
            curr_vol = hist['Volume'].iloc[-1]
            rvol = round(curr_vol / avg_vol, 2) if avg_vol > 0 else 1.0

            # 7-Tage-Spanne (Hoch/Tief)
            low_7d = hist['Low'].min()
            high_7d = hist['High'].max()
            range_pos = ((current_price - low_7d) / (high_7d - low_7d)) * 100 if (high_7d - low_7d) > 0 else 50

            # News (nur die Top 3 Schlagzeilen)
            news_items = []
            try:
                raw_news = ticker.news[:3]
                for n in raw_news:
                    news_items.append({'title': n.get('title'), 'link': n.get('link')})
            except:
                news_items = []

            results.append({
                'name': name,
                'symbol': symbol,
                'price': round(current_price, 2),
                'change': round(change_pct, 2),
                'rvol': rvol,
                'range_pos': round(range_pos, 0),
                'news': news_items
            })
        except Exception as e:
            print(f"Fehler bei {name}: {e}")
            continue

    return results, vix, eur_usd

@app.route('/')
def index():
    data, vix, eur_usd = get_market_data()
    
    # HTML-Template mit modernem Dark-Mode & Blink-Effekt bei RVOL > 3
    html = """
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gschmäckle-Radar</title>
        <style>
            body { background: #121212; color: #e0e0e0; font-family: sans-serif; margin: 10px; }
            .header { display: flex; justify-content: space-between; padding: 10px; background: #1e1e1e; border-radius: 8px; margin-bottom: 15px; }
            .card { background: #1e1e1e; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #333; }
            .alarm { border-left: 5px solid #ff5252; animation: blink 2s infinite; }
            @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }
            .price { font-size: 1.2em; font-weight: bold; }
            .pos { color: #4caf50; } .neg { color: #ff5252; }
            .news-box { font-size: 0.85em; margin-top: 10px; padding-top: 10px; border-top: 1px solid #333; }
            .news-link { color: #81d4fa; text-decoration: none; display: block; margin-bottom: 5px; }
            .range-bg { background: #333; height: 8px; border-radius: 4px; margin-top: 5px; width: 100%; }
            .range-bar { background: #81d4fa; height: 100%; border-radius: 4px; }
            .footer { font-size: 0.7em; color: #666; text-align: center; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <span>VIX: <b>{{ vix }}</b></span>
            <span>EUR/USD: <b>{{ eur_usd }}</b></span>
        </div>

        {% for item in data %}
        <div class="card {{ 'alarm' if item.rvol > 3 else '' }}">
            <div style="display: flex; justify-content: space-between;">
                <b>{{ item.name }}</b>
                <span class="price">{{ item.price }}</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                <span class="{{ 'pos' if item.change >= 0 else 'neg' }}">{{ item.change }}%</span>
                <span>RVOL: <b>{{ item.rvol }}</b></span>
            </div>
            
            <div class="range-bg"><div class="range-bar" style="width: {{ item.range_pos }}%;"></div></div>

            {% if item.news %}
            <div class="news-box">
                {% for n in item.news %}
                <a class="news-link" href="{{ n.link }}" target="_blank">📰 {{ n.title }}</a>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endfor %}

        <div class="footer">
            Privates Experiment. Keine Anlageberatung. Daten ohne Gewähr.<br>
            Stand: {{ now.strftime('%H:%M:%S') }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html, data=data, vix=round(vix, 2), eur_usd=round(eur_usd, 4), now=datetime.datetime.now())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
