import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

TICKERS = {
    "Bitcoin": "BTC-USD", "Öl WTI": "CL=F", "Öl Brent": "BZ=F",
    "Gold": "GC=F", "Silber": "SI=F", "Kupfer": "HG=F",
    "S&P 500": "^GSPC", "DAX": "^GDAXI", "Nikkei 225": "^N225",
    "Hang Seng": "^HSI", "EUR/USD": "EURUSD=X"
}

DINO_ICON_URL = "https://files.catbox.moe/546s3n.png" 

def format_de(v, d=2):
    if v is None or pd.isna(v): return "N/A"
    try: return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "N/A"

def get_single_ticker_data(args):
    name, symbol = args
    try:
        t = yf.Ticker(symbol)
        h = t.history(period="2d")
        if h.empty: return None
        curr = h['Close'].iloc[-1]
        prev = h['Close'].iloc[-2] if len(h) > 1 else curr
        change = ((curr - prev) / prev) * 100 if prev else 0.0
        
        rvol = None
        if name in ["Öl WTI", "Öl Brent"]:
            hist = t.history(period="60d")
            if len(hist) >= 30:
                v_t, v_m = hist['Volume'].iloc[-1], hist['Volume'].iloc[:-1].median()
                if v_m > 0: rvol = round(v_t / v_m, 2)
        
        h7 = t.history(period="7d")
        l7, hi7 = h7['Low'].min(), h7['High'].max()
        range_pos = ((curr - l7) / (hi7 - l7)) * 100 if (hi7 - l7) > 0 else 50
        ampel = "red" if change < 0 else "green"
        if rvol and rvol >= 3.0: ampel = "red" if change < 0 else "green"
        elif rvol and rvol < 0.8: ampel = "yellow"
            
        return {
            'name': name, 'symbol': symbol, 'ampel': ampel, 
            'price_val': curr, 'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)), 
            'change_val': change, 'change': format_de(change, 2), 
            'rvol': rvol, 'range_pos': round(range_pos, 0), 'is_pos': change >= 0,
            'url': f"https://finance.yahoo.com/quote/{symbol}"
        }
    except: return None

@app.route('/')
def index():
    try:
        v_t = yf.Ticker("^VIX")
        v_h = v_t.history(period="2d")
        vix_v = v_h['Close'].iloc[-1]
        vix_p = ((vix_v - v_h['Close'].iloc[-2]) / v_h['Close'].iloc[-2]) * 100
    except: vix_v, vix_p = 20.0, 0.0
    
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = [r for r in list(ex.map(get_single_ticker_data, TICKERS.items())) if r is not None]
    
    prices = {r['name']: r['price_val'] for r in results}
    changes = {r['name']: r['change_val'] for r in results}
    gs_val = prices.get("Gold", 0) / prices.get("Silber", 1) if "Gold" in prices and "Silber" in prices else 0
    gs_c = "#ffd700" if changes.get("Gold", 0) > changes.get("Silber", 0) else "#c0c0c0"
    
    ki_data = f"MARKET UPDATE {datetime.now().strftime('%d.%m.%Y')}\\n"
    ki_data += f"VIX: {format_de(vix_v)} ({format_de(vix_p)}%)\\n"
    ki_data += f"Gold/Silber Ratio: {format_de(gs_val)}\\n"
    for r in results:
        ki_data += f"{r['name']}: {r['price']} ({r['change']}%)\\n"

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="{DINO_ICON_URL}"><link rel="apple-touch-icon" href="{DINO_ICON_URL}">
    <title>Radar</title>
    <style>
    body {{ background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; padding-bottom: 30px; }}
    .header {{ display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-weight: bold; align-items: center; }}
    .header a {{ color: inherit; text-decoration: none; }}
    .btn {{ background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; height: 55px; font-size: 1.1em; }}
    .card {{ background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }}
    .border-red {{ border-left-color: #ff5252; }} .border-yellow {{ border-left-color: #ffd740; }} .border-green {{ border-left-color: #4caf50; }}
    .row {{ display: flex; justify-content: space-between; align-items: center; }}
    a {{ color: inherit; text-decoration: none; display: block; width: 100%; }}
    .price-text {{ font-weight: 900; font-size: 1.2em; }}
    .text-green {{ color: #4caf50; }} .text-red {{ color: #ff5252; }}
    .range-bg {{ background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }}
    .range-bar {{ height: 100%; border-radius: 3px; }}
    .bg-red {{ background-color: #ff5252; }} .bg-yellow {{ background-color: #ffd740; }} .bg-green {{ background-color: #4caf50; }}
    .footer {{ text-align: center; font-size: 0.72em; color: #555; margin-top: 30px; line-height: 1.6; border-top: 1px solid #222; padding: 20px 10px; }}
    </style>
    <script>
    function copyData() {{
        const text = "{ki_data}";
        navigator.clipboard.writeText(text.replace(/\\\\n/g, '\\n')).then(() => {{
            const btn = document.querySelector('.btn');
            btn.innerText = "WERTE KOPIERT! ✅";
            btn.style.background = "#4caf50";
            setTimeout(() => {{
                btn.innerText = "SHORTCUT 2 ANALYSE AKTIV 🚀";
                btn.style.background = "linear-gradient(45deg, #f1c40f, #f39c12)";
            }}, 2000);
        }});
    }}
    </script>
    </head><body>
    <div class="header">
        <a href="https://finance.yahoo.com/quote/%5EVIX" target="_blank">VIX: <b>{format_de(vix_v)}</b> ({format_de(vix_p)}%)</a>
        <span>G/S: <b style="color:{gs_c};">{format_de(gs_val)}</b></span>
    </div>
    <button class="btn" onclick="copyData()">SHORTCUT 2 ANALYSE AKTIV 🚀</button>
    """
    for item in results:
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
        BERLIN: {(datetime.now() + timedelta(hours=2)).strftime('%H:%M:%S')}<br><br>
        <b>DISCLAIMER:</b> Alle Daten dienen ausschließlich der Information und stellen keine Anlageberatung oder Handelsempfehlung dar. Der Handel mit Wertpapieren und Rohstoffen birgt hohe Risiken bis hin zum Totalverlust. Daten können zeitverzögert sein. Nutzung auf eigene Gefahr.
    </div>
    </body></html>"""
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
