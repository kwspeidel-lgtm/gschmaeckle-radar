import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Preis-Ticker (Was du siehst)
TICKERS = {
    "Bitcoin": "BTC-USD", "Öl WTI": "CL=F", "Öl Brent": "BZ=F",
    "Gold": "GC=F", "Silber": "SI=F", "Kupfer": "HG=F",
    "S&P 500": "^GSPC", "DAX": "^GDAXI", "Nikkei 225": "^N225",
    "Hang Seng": "^HSI", "EUR/USD": "EURUSD=X"
}

# Volumen-Quellen (ETFs für stabilen VQ)
VOL_SOURCES = {
    "Gold": "GLD", "Silber": "SLV", "Öl WTI": "USO", 
    "Öl Brent": "BNO", "Kupfer": "CPER"
}

DINO_ICON_URL = "https://files.catbox.moe/546s3n.png"

def format_de(v, d=2):
    if v is None or pd.isna(v): return "N/A"
    try: return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "N/A"

def get_pace_factor():
    now = datetime.now() + timedelta(hours=2) # Berlin
    start, end = now.replace(hour=8, minute=0), now.replace(hour=22, minute=0)
    if now < start: return 0.05
    if now > end: return 1.0
    return max(0.05, (now - start).total_seconds() / (end - start).total_seconds())

def get_single_ticker_data(args):
    name, symbol = args
    pace_f = get_pace_factor()
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        curr, prev = fi['last_price'], fi['previous_close']
        if pd.isna(curr) or curr == 0: curr = t.history(period="1d")['Close'].iloc[-1]
        change = ((curr - prev) / prev) * 100 if prev else 0.0
        
        vq = None
        vol_ticker_sym = VOL_SOURCES.get(name)
        if vol_ticker_sym:
            vt = yf.Ticker(vol_ticker_sym)
            v_hist = vt.history(period="90d")
            if len(v_hist) >= 30:
                avg_v = v_hist['Volume'].iloc[:-1].mean()
                cur_v = vt.fast_info.get('base_volume', v_hist['Volume'].iloc[-1])
                if avg_v > 0: vq = round(cur_v / (avg_v * pace_f), 2)

        h7 = t.history(period="7d")
        l7, hi7 = h7['Low'].min(), h7['High'].max()
        r_pos = ((curr - l7) / (hi7 - l7)) * 100 if (hi7 - l7) > 0 else 50
        
        ampel = "green" if change >= 0 else "red"
        if vq is not None:
            if vq < 0.4: ampel = "yellow"
            elif vq > 2.5: ampel = "green" if change >= 0 else "red"

        return {'name': name, 'symbol': symbol, 'ampel': ampel, 'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)), 'change_val': change, 'change': format_de(change, 2), 'vq': vq, 'range_pos': round(r_pos, 0), 'is_pos': change >= 0, 'url': f"https://finance.yahoo.com/quote/{symbol}"}
    except: return None

@app.route('/')
def index():
    try:
        v_t = yf.Ticker("^VIX")
        vix_v = v_t.fast_info['last_price']
        vix_p = ((vix_v - v_t.fast_info['previous_close']) / v_t.fast_info['previous_close']) * 100
        vix_ampel = "red" if vix_v > 25 else ("yellow" if vix_v > 20 else "green")
    except: vix_v, vix_p, vix_ampel = 20.0, 0.0, "green"
    
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = [r for r in list(ex.map(get_single_ticker_data, TICKERS.items())) if r is not None]
    
    g = next((r for r in results if r['name']=="Gold"), None)
    s = next((r for r in results if r['name']=="Silber"), None)
    gs_val = float(g['price'].replace('.','').replace(',','.'))/float(s['price'].replace('.','').replace(',','.')) if g and s else 0
    gs_c = "#ffd700" if (g['change_val'] if g else 0) > (s['change_val'] if s else 0) else "#c0c0c0"
    gs_ampel = "green" if (g['change_val'] if g else 0) > 0 else "red"

    ki_data = f"MARKET UPDATE {datetime.now().strftime('%d.%m.%Y %H:%M')}\\n"
    ki_data += f"VIX: {format_de(vix_v)} ({format_de(vix_p)}%)\\nGS Ratio: {format_de(gs_val)}\\n"
    for r in results:
        ki_data += f"{r['name']}: {r['price']} ({r['change']}%" + (f", VQ: {r['vq']})" if r['vq'] else ")") + "\\n"

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="{DINO_ICON_URL}"><title>Radar</title>
    <style>
    body {{ background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }}
    .header-box {{ display: flex; justify-content: space-between; margin-bottom: 12 daring; gap: 10px; }}
    .h-item {{ flex: 1; padding: 15px; background: #111; border-radius: 12px; border-left: 5px solid #333; font-weight: bold; text-align: center; text-decoration: none; color: inherit; }}
    .btn {{ background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; height: 55px; font-size: 1.1em; }}
    .card {{ background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }}
    .border-red {{ border-left-color: #ff5252; }} .border-yellow {{ border-left-color: #ffd740; }} .border-green {{ border-left-color: #4caf50; }}
    .row {{ display: flex; justify-content: space-between; align-items: center; }}
    .price-text {{ font-weight: 900; font-size: 1.2em; }}
    .text-green {{ color: #4caf50; }} .text-red {{ color: #ff5252; }}
    .range-bg {{ background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }}
    .range-bar {{ height: 100%; border-radius: 3px; }}
    .bg-red {{ background-color: #ff5252; }} .bg-yellow {{ background-color: #ffd740; }} .bg-green {{ background-color: #4caf50; }}
    .footer {{ text-align: center; font-size: 1.1em; color: #fff; margin-top: 30px; line-height: 1.6; border-top: 1px solid #333; padding-top: 20px; }}
    </style>
    <script>
    function copyData() {{
        const text = "{ki_data}";
        navigator.clipboard.writeText(text.replace(/\\\\n/g, '\\n')).then(() => {{
            const btn = document.querySelector('.btn');
            btn.innerText = "KOPIERT! ✅"; btn.style.background = "#4caf50";
            setTimeout(() => {{ btn.innerText = "SHORTCUT 2 ANALYSE AKTIV 🚀"; btn.style.background = "linear-gradient(45deg, #f1c40f, #f39c12)"; }}, 2000);
        }});
    }}
    </script>
    </head><body>
    <div class="header-box">
        <a href="https://finance.yahoo.com/quote/^VIX" class="h-item border-{vix_ampel}">VIX: {format_de(vix_v)}</a>
        <div class="h-item border-{gs_ampel}">G/S: <span style="color:{gs_c};">{format_de(gs_val)}</span></div>
    </div>
    <button class="btn" onclick="copyData()">SHORTCUT 2 ANALYSE AKTIV 🚀</button>
    """
    for item in results:
        html += f"""<div class="card border-{item['ampel']}"><a href="{item['url']}" target="_blank" style="color:inherit; text-decoration:none;">
        <div class="row"><b>{item['name']}</b><span class="price-text {'text-green' if item['is_pos'] else 'text-red'}">{item['price']}</span></div>
        <div class="row" style="margin-top:8px;"><span style="font-weight:800; color: {'#4caf50' if item['is_pos'] else '#ff5252'};">{item['change']}%</span>
        {f'<span style="font-size:0.85em; font-weight:800; padding:4px; background:#222; border-radius:6px;">VQ: {item["vq"]}</span>' if item['vq'] else ''}</div>
        <div class="range-bg"><div class="range-bar bg-{item['ampel']}" style="width:{item['range_pos']}%"></div></div></a></div>"""
    
    html += f"""<div class="footer"><b>BERLIN: {(datetime.now() + timedelta(hours=2)).strftime('%H:%M:%S')}</b><br><br><i>Disclaimer: Keine Anlageberatung. Handel auf eigenes Risiko. Alle Daten ohne Gewähr.</i></div></body></html>"""
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
