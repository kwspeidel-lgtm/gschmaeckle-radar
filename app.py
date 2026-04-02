import os
import pandas as pd
import yfinance as yf
from flask import Flask, render_template_string
from datetime import datetime, timedelta, time
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

def get_pace_factor():
    """Berechnet, wie viel Prozent des Handelstages (8-22 Uhr) vergangen sind."""
    now = datetime.now() + timedelta(hours=2) # Berlin Zeit
    start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    end = now.replace(hour=22, minute=0, second=0, microsecond=0)
    
    if now < start: return 0.05 # Vor der Börse minimaler Faktor
    if now > end: return 1.0    # Nach der Börse voller Tag
    
    total_seconds = (end - start).total_seconds()
    elapsed_seconds = (now - start).total_seconds()
    return max(0.05, elapsed_seconds / total_seconds)

def get_single_ticker_data(args):
    name, symbol = args
    pace_factor = get_pace_factor()
    try:
        t = yf.Ticker(symbol)
        fi = t.fast_info
        curr = fi['last_price']
        prev = fi['previous_close']
        if pd.isna(curr) or curr == 0:
            curr = t.history(period="1d")['Close'].iloc[-1]
        change = ((curr - prev) / prev) * 100 if prev else 0.0
        
        vq_pace = None
        # Volumen-Check für Rohstoffe
        if name in ["Öl WTI", "Öl Brent", "Gold", "Silber", "Kupfer"]:
            hist = t.history(period="90d")
            if len(hist) >= 30:
                avg_vol = hist['Volume'].iloc[:-1].mean()
                curr_vol = fi.get('base_volume', hist['Volume'].iloc[-1])
                # Pace Logik: Aktuelles Vol / (Soll-Volumen bis jetzt)
                if avg_vol > 0:
                    vq_pace = round(curr_vol / (avg_vol * pace_factor), 2)
        
        h7 = t.history(period="7d")
        l7, hi7 = h7['Low'].min(), h7['High'].max()
        range_pos = ((curr - l7) / (hi7 - l7)) * 100 if (hi7 - l7) > 0 else 50
        
        # Intelligente Ampel
        ampel = "green" if change >= 0 else "red"
        if vq_pace is not None:
            if vq_pace < 0.4: ampel = "yellow" # Fake-Trend (wenig Druck)
            elif vq_pace > 2.5: ampel = "green" if change >= 0 else "red" # Power-Trend (hoher VQ)
            
        return {'name': name, 'symbol': symbol, 'ampel': ampel, 'price': format_de(curr, 2 if "USD" not in symbol and "EUR" not in symbol else (0 if "BTC" in symbol else 4)), 'change_val': change, 'change': format_de(change, 2), 'vq': vq_pace, 'range_pos': round(range_pos, 0), 'is_pos': change >= 0, 'url': f"https://finance.yahoo.com/quote/{symbol}"}
    except: return None

@app.route('/')
def index():
    try:
        v_t = yf.Ticker("^VIX")
        vix_v = v_t.fast_info['last_price']
        vix_p = ((vix_v - v_t.fast_info['previous_close']) / v_t.fast_info['previous_close']) * 100
    except: vix_v, vix_p = 20.0, 0.0
    
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = [r for r in list(ex.map(get_single_ticker_data, TICKERS.items())) if r is not None]
    
    gs_val = 0
    g_p = next((r for r in results if r['name'] == "Gold"), None)
    s_p = next((r for r in results if r['name'] == "Silber"), None)
    if g_p and s_p:
        # Extrahiere floats für Ratio
        try:
            g_f = float(g_p['price'].replace('.', '').replace(',', '.'))
            s_f = float(s_p['price'].replace('.', '').replace(',', '.'))
            gs_val = g_f / s_f
        except: pass
    
    gs_c = "#ffd700" if (g_p['change_val'] if g_p else 0) > (s_p['change_val'] if s_p else 0) else "#c0c0c0"
    
    # KI-DATA (Kopieren)
    ki_data = f"MARKET UPDATE {datetime.now().strftime('%d.%m.%Y %H:%M')}\\n"
    ki_data += f"VIX: {format_de(vix_v)} ({format_de(vix_p)}%)\\n"
    ki_data += f"G/S Ratio: {format_de(gs_val)}\\n"
    for r in results:
        ki_data += f"{r['name']}: {r['price']} ({r['change']}%"
        if r['vq']: ki_data += f", VQ: {r['vq']}"
        ki_data += ")\\n"

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="{DINO_ICON_URL}"><link rel="apple-touch-icon" href="{DINO_ICON_URL}">
    <title>Radar</title>
    <style>
    body {{ background: #000; color: #e0e0e0; font-family: sans-serif; margin: 10px; }}
    .header {{ display: flex; justify-content: space-between; padding: 15px; background: #111; border-radius: 12px; margin-bottom: 12px; border: 1px solid #222; font-weight: bold; }}
    .btn {{ background: linear-gradient(45deg, #f1c40f, #f39c12); color: #000; border: none; padding: 15px; border-radius: 12px; font-weight: 900; width: 100%; margin-bottom: 15px; cursor: pointer; height: 55px; font-size: 1.1em; }}
    .card {{ background: #111; padding: 15px; border-radius: 14px; margin-bottom: 10px; border-left: 7px solid #333; }}
    .border-red {{ border-left-color: #ff5252; }} .border-yellow {{ border-left-color: #ffd740; }} .border-green {{ border-left-color: #4caf50; }}
    .row {{ display: flex; justify-content: space-between; align-items: center; }}
    .price-text {{ font-weight: 900; font-size: 1.2em; }}
    .text-green {{ color: #4caf50; }} .text-red {{ color: #ff5252; }}
    .range-bg {{ background: #1a1a1a; height: 6px; border-radius: 3px; margin: 12px 0; }}
    .range-bar {{ height: 100%; border-radius: 3px; }}
    .bg-red {{ background-color: #ff5252; }} .bg-yellow {{ background-color: #ffd740; }} .bg-green {{ background-color: #4caf50; }}
    .footer {{ text-align: center; font-size: 0.75em; color: #444; margin-top: 20px; line-height: 1.4; }}
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
        <span>VIX: <b>{format_de(vix_v)}</b></span>
        <span>G/S: <b style="color:{gs_c};">{format_de(gs_val)}</b></span>
    </div>
    <button class="btn" onclick="copyData()">SHORTCUT 2 ANALYSE AKTIV 🚀</button>
    """
    for item in results:
        html += f"""
        <div class="card border-{item['ampel']}">
            <a href="{item['url']}" target="_blank" style="color:inherit; text-decoration:none;">
                <div class="row"><b>{item['name']}</b><span class="price-text {'text-green' if item['is_pos'] else 'text-red'}">{item['price']}</span></div>
                <div class="row" style="margin-top:8px;">
                    <span style="font-weight:800; color: {'#4caf50' if item['is_pos'] else '#ff5252'};">{item['change']}%</span>
                    {f'<span style="font-size:0.85em; font-weight:800; padding:4px; background:#222; border-radius:6px;">VQ: {item["vq"]}</span>' if item['vq'] else ''}
                </div>
                <div class="range-bg"><div class="range-bar bg-{item['ampel']}" style="width:{item['range_pos']}%"></div></div>
            </a>
        </div>"""
    
    html += f"""<div class="footer">BERLIN: {(datetime.now() + timedelta(hours=2)).strftime('%H:%M:%S')}<br><br><i>Disclaimer: Keine Anlageberatung. Handel auf eigenes Risiko.</i></div></body></html>"""
    return html

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
