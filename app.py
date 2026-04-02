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
        hist = t.history(period="90d")
        if hist.empty: return None
        
        curr = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2] if len(hist) > 1 else curr
        change = ((curr - prev) / prev) * 100
        
        # NEU: Volumen-Quotient (VQ) Berechnung
        vq = None
        if name in ["Öl WTI", "Öl Brent", "Gold", "Silber", "Kupfer"]:
            vol_today = hist['Volume'].iloc[-1]
            vol_avg = hist['Volume'].iloc[:-1].mean()
            if vol_avg > 0:
                vq = round(vol_today / vol_avg, 2)
        
        # NEUE AMPEL-LOGIK (VQ-basiert)
        # Gelb bei zu wenig Volumen (Fake-Gefahr)
        if vq is not None and vq < 0.5:
            ampel = "yellow"
        # Rot/Grün bei normalem/hohem Volumen
        else:
            ampel = "green" if change >= 0 else "red"
            
        h7 = hist.tail(7)
        l7, hi7 = h7['Low'].min(), h7['High'].max()
        range_pos = ((curr - l7) / (hi7 - l7)) * 100 if (hi7 - l7) > 0 else 50
            
        return {
            'name': name, 'symbol': symbol, 'ampel': ampel, 
            'price_val': curr, 'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)), 
            'change_val': change, 'change': format_de(change, 2), 
            'vq': vq, 'range_pos': round(range_pos, 0), 
            'is_pos': change >= 0, 'url': f"https://finance.yahoo.com/quote/{symbol}"
        }
    except: return None

@app.route('/')
def index():
    try:
        v_t = yf.Ticker("^VIX")
        vix_h = v_t.history(period="2d")
        vix_v = vix_h['Close'].iloc[-1]
        vix_p = ((vix_v - vix_h['Close'].iloc[-2]) / vix_h['Close'].iloc[-2]) * 100
    except: vix_v, vix_p = 20.0, 0.0
    
    # Reduzierte Worker für schnelleren Start auf Render Free Tier
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = [r for r in list(ex.map(get_single_ticker_data, TICKERS.items())) if r is not None]
    
    prices = {r['name']: r['price_val'] for r in results}
    changes = {r['name']: r['change_val'] for r in results}
    
    gs_val = prices.get("Gold", 0) / prices.get("Silber", 1) if "Gold" in prices and "Silber" in prices else 0
    gs_c = "#ffd700" if changes.get("Gold", 0) > changes.get("Silber", 0) else "#c0c0c0"
    
    # KI-DATENBLOCK (Inklusive VQ für Rohstoffe)
    ki_data = f"MARKET UPDATE {datetime.now().strftime('%d.%m.%Y')}\\n"
    ki_data += f"VIX: {format_de(vix_v)} ({format_de(vix_p)}%)\\n"
    ki_data += f"Gold/Silber Ratio: {format_de(gs_val)}\\n"
    for r in results:
        ki_data += f"{r['name']}: {r['price']} ({r['change']}%"
        if r['vq']: ki_data += f", VQ: {r['vq']}"
        ki_data += ")\\n"

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="{DINO_ICON_URL}"><link rel="apple-touch-icon" href="{DINO_ICON_URL}">
    <title>Radar</title>
    <style>
    body {{ background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }}
    .header {{ display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-weight: bold; font-size: 0.9em; }}
    .btn {{ background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; height: 55px; font-size: 1.1em; }}
    .card {{ background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }}
    .border-red {{ border-left-color: #ff5252; }} .border-yellow {{ border-left-color: #ffd740; }} .border-green {{ border-left-color: #4caf50; }}
    .row {{ display: flex; justify-content: space-between; align-items: center; }}
    a {{ color: inherit; text-decoration: none; display: block; }}
    .price-text {{ font-weight: 900; font-size: 1.2em; }}
    .text-green {{ color: #4caf50; }} .text-red {{ color: #ff5252; }}
    .range-bg {{ background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }}
    .range-bar {{ height: 100%; border-radius: 3px; }}
    .bg-red {{ background-color: #ff5252; }} .bg-yellow {{ background-color: #ffd740; }} .bg-green {{ background-color: #4caf50; }}
    .footer {{ text-align: center; font-size: 0.75em; color: #444; margin-top: 20px; padding: 10px; line-height: 1.4; }}
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
        <span>VIX: <b>{format_de(vix_v)}</b> ({format_de(vix_p)}%)</span>
        <span>G/S: <b style="color:{gs_c};">{format_de(gs_val)}</b></span>
    </div>
    <button class="btn" onclick="copyData()">SHORTCUT 2 ANALYSE AKTIV 🚀</button>
    """
    for item in results:
        # VQ-Label nur anzeigen wenn berechnet
        vq_label = f'<span style="font-size:0.8em; font-weight:800; padding:3px 6px; background:#222; border-radius:5px; color:{"#ff5252" if item["vq"] > 3.0 else "#e0e0e0"}">VQ: {item["vq"]}</span>' if item['vq'] else ""
        
        html += f"""
        <div class="card border-{item['ampel']}">
            <a href="{item['url']}" target="_blank">
                <div class="row"><b>{item['name']}</b><span class="price-text {'text-green' if item['is_pos'] else 'text-red'}">{item['price']}</span></div>
                <div class="row" style="margin-top:8px;">
                    <span style="font-weight:800; color: {'#4caf50' if item['is_pos'] else '#ff5252'};">{item['change']}%</span>
                    {vq_label}
                </div>
                <div class="range-bg"><div class="range-bar bg-{item['ampel']}" style="width:{item['range_pos']}%"></div></div>
            </a>
        </div>"""
    
    html += f"""<div class="footer">BERLIN: {(datetime.now() + timedelta(hours=2)).strftime('%H:%M:%S')}<br><br><i>Disclaimer: Alle Daten sind ohne Gewähr. Dies ist keine Anlageberatung. Handel auf eigenes Risiko.</i></div></body></html>"""
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
