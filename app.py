import os
from flask import Flask
import pandas as pd
from twelvedata import TDClient
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURATION ---
API_KEY = "0c4ce2fcaffa4f1592e012cfef854161"
SYMBOLS = ["BTC/USD", "WTI/USD", "LCO/USD", "XAU/USD", "XAG/USD", "DXY", "VIX", "DAX", "SPX", "FGBL"]

@app.route('/')
def gschmaeckle_radar():
    td = TDClient(apikey=API_KEY)
    now = datetime.now()
    
    # Header für die Web-Anzeige
    html = f"""
    <html>
    <head><title>Gschmäckle Insider Radar</title></head>
    <body style="font-family: monospace; background-color: #121212; color: #00ff00; padding: 20px;">
        <h1>GSCHMÄCKLE INSIDER RADAR</h1>
        <p>Zeitpunkt: {now.strftime('%d.%m.%Y %H:%M:%S')}</p>
        <hr>
        <table border="0" cellpadding="10">
            <tr>
                <th align="left">Asset</th>
                <th align="left">Preis</th>
                <th align="left">Status</th>
            </tr>
    """

    try:
        # Batch-Abruf der aktuellen Kurse
        quotes = td.quote(symbol=SYMBOLS).as_json()
        
        for symbol in SYMBOLS:
            # Check falls nur ein Symbol zurückkommt (API Besonderheit)
            q = quotes[symbol] if len(SYMBOLS) > 1 else quotes
            price = float(q['close'])
            change = float(q.get('percent_change', 0))
            
            # Einfache Status-Ampel
            color = "#00ff00" if change >= 0 else "#ff4444"
            status = "STABIL"
            if abs(change) > 2.0:
                status = "⚠️ VOLATIL"

            html += f"""
            <tr>
                <td>{symbol}</td>
                <td style="color: {color};">{price:.2f} ({change:+.2f}%)</td>
                <td>{status}</td>
            </tr>
            """
            
        html += "</table><p><br><i>Seite neu laden für frische API-Daten.</i></p></body></html>"
        
    except Exception as e:
        html += f"<p style='color: orange;'>Warte auf API oder Limit erreicht: {str(e)}</p>"
    
    return html

if __name__ == "__main__":
    # Render nutzt den Port aus den Environment Variables
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
