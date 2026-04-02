import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string, jsonify
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

TICKERS = {
    "Bitcoin": "BTC-USD",
    "Öl WTI": "CL=F", "Öl Brent": "BZ=F",
    "Gold": "GC=F", "Silber": "SI=F", "Kupfer": "HG=F",
    "S&P 500": "^GSPC", "DAX": "^GDAXI", "Nikkei 225": "^N225",
    "Hang Seng": "^HSI", "EUR/USD": "EURUSD=X"
}

# Der direkte Link zu deinem Dino (Quadratisch, 512x512)
DINO_ICON_URL = "https://files.catbox.moe/546s3n.png" 

def format_de(v, d=2):
    if v is None or pd.isna(v): return "N/A"
    try:
        return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "N/A"

def get_single_ticker_data(args):
    name, symbol = args
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        curr = fi['last_price']
        prev = fi['previous_close']
        if pd.isna(curr) or curr == 0:
            curr = t.history(period="1d")['Close'].iloc[-1]
        change = ((curr - prev) / prev) * 100 if prev else 0.0
        
        rvol = None
        if name in ["Öl WTI", "Öl Brent"]:
            hist = t.history(period="60d")
            if len(hist) >= 30:
                v_t, v_m = hist['Volume'].iloc[-1], hist['Volume'].iloc[:-1].median()
                if v_m > 0:
                    rvol = round(v_t / v_m, 2)
        
        h7 = t.history(period="7d")
        l7, hi7 = h7['Low'].min(), h7['High'].max()
        range_pos = ((curr - l7) / (hi7 - l7)) * 100 if (hi7 - l7) > 0 else 50
        
        ampel = "red" if change < 0 else "green"
        if rvol and rvol >= 3.0: ampel = "red" if change < 0 else "green"
        elif rvol and rvol < 0.8: ampel = "yellow"
            
        return {'name': name, 'symbol': symbol, 'ampel': ampel, 'price_val': curr, 'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)), 'change_val': change, 'change': format_de(change, 2), 'rvol': rvol, 'range_pos': round(range_pos, 0), 'is_pos': change >= 0, 'url': f"https://finance.yahoo.com/quote/{symbol}"}
    except: return None

def get_market_data():
    try:
        v_t = yf.Ticker("^VIX")
        vix_curr = v_t.fast_info['last_price']
        vix_prev = v_t.fast_info['previous_close']
        vix_change = ((vix_curr - vix_prev) / vix_prev) * 100
    except: vix_curr, vix_change = 20.0, 0.0
    
    with ThreadPoolExecutor(max_workers=12) as ex:
        results = [r for r in list(ex.map(get_single_ticker_data, TICKERS.items())) if r is not None]
    
    prices = {r['name']: r['price_val'] for r in results}
    changes = {r['name']: r['change_val'] for r in results}
    gs_val = prices.get("Gold", 0) / prices.get("Silber", 1) if "Gold" in prices and "Silber" in prices else 0
    gs_color = "#ffd700" if changes.get("Gold", 0) > changes.get("Silber", 0) else "#c0c0c0"
    
    return results, format_de(vix_curr), format_de(vix_change), gs_val, gs_color, datetime.now() + timedelta(hours=2)

@app.route('/')
def index():
    data, vix_v, vix_p, gs_v, gs_c, now_time = get_market_data()
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <link rel="icon" type="image/png" sizes="192x192" href="{DINO_ICON_URL}">
    <link rel="icon" type="image/png" sizes="512x512" href="{DINO_ICON_URL}">
    <link rel="apple-touch-icon" href="{DINO_ICON_URL}">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#000000">

    <title>Radar</title>
    <style>
    body {{ background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }}
    .header {{ display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-weight: bold; }}
    .btn {{ background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: default; height: 55px; font-size: 1.1em; text-align: center; line-height: 25px; }}
    .card {{ background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }}
    .border-red {{ border-left-color: #ff5252; }} .border-yellow {{ border-left-color: #ffd740; }} .border-green {{ border-left-color: #4caf50; }}
    .row {{ display: flex; justify-content: space-between; align-items: center; }}
    a {{ color: inherit; text-decoration: none; display: block; }}
    .price-text {{ font-weight: 900; font-size: 1.2em; text-align: right; }}
    .text-green {{ color: #4caf50; }} .text-red {{ color: #ff5252; }}
    .range-bg {{ background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }}
    .range-bar {{ height: 100%; border-radius: 3px; }}
    .bg-red {{ background-color: #ff5252; }} .bg-yellow {{ background-color: #ffd740; }} .bg-green {{ background-color: #4caf50; }}
    .footer {{ text-align: center; font-size: 0.75em; color: #444; margin-top: 20px; line-height: 1.4; }}
    </style></head><body>
    <div class="header">
        <span>VIX: <b>{vix_v}</b> ({vix_p}%)</span>
        <span>G/S: <b style="color:{gs_c};">{format_de(gs_v)}</b></span>
    </div>
    <div class="btn">SHORTCUT 2 ANALYSE AKTIV 🚀</div>
    """
    for item in data:
        html += f"""
        <div class="card border-{item['ampel']}">
            <a href="{item['url']}" target="_blank">
                <div class="row"><b>{item['name']}</b><span class="price-text {'text-green' if item['is_pos'] else 'text-red'}">{item['price']}</span></div>
                <div class="row" style="margin-top:8px;">
                    <span style="font-weight:800; color: {'#4caf50' if item['is_pos'] else '#ff5252'};">{item['change']}%</span>
                    {f'<span style="font-size:0.85em; font-weight:800; padding:4px; background:#222; border-radius:6px;">RVOL: {item["rvol"]}</span>' if item['rvol'] else ''}
                </div>
                <div class="range-bg"><div class="range-bar bg-{item['ampel']}" style="width:{item['range_pos']}%"></div></div>
            </a>
        </div>"""
    
    html += f"""
    <div class="footer">
        BERLIN: {now_time.strftime('%H:%M:%S')}<br><br>
        <i>Disclaimer: Alle Daten sind ohne Gewähr. Dies ist keine Anlageberatung.<br>Handel auf eigenes Risiko.</i>
    </div>
    </body></html>"""
    return html

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
