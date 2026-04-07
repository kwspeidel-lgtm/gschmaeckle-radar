import os
from flask import Flask
from twelvedata import TDClient
from datetime import datetime

app = Flask(__name__)

# --- KONFIGURATION ---
API_KEY = "0c4ce2fcaffa4f1592e012cfef854161"
# Auf 7 Symbole gekürzt, um das 8-Credit-Limit pro Minute zu unterschreiten
SYMBOLS = ["BTC/USD", "WTI/USD", "LCO/USD", "XAU/USD", "XAG/USD", "DXY", "VIX"]

@app.route('/')
def gschmaeckle_radar():
    td = TDClient(apikey=API_KEY)
    now = datetime.now()
    
    html = f"""
    <html>
    <head>
        <title>Gschmäckle Insider Radar</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body style="font-family: 'Courier New', monospace; background-color: #000; color: #0f0; padding: 20px;">
        <h1 style="border-bottom: 1px solid #0f0; padding-bottom: 10px;">GSCHMÄCKLE RADAR</h1>
        <p>Status: ONLINE | {now.strftime('%H:%M:%S')}</p>
        <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <tr style="border-bottom: 1px solid #333;">
                <th align="left" style="padding: 10px;">Asset</th>
                <th align="left" style="padding: 10px;">Preis (USD)</th>
                <th align="left" style="padding: 10px;">%</th>
            </tr>
    """

    try:
        # Ein Call = 7 Credits. Das passt perfekt in das 8er-Limit!
        quotes = td.quote(symbol=SYMBOLS).as_json()
        
        for symbol in SYMBOLS:
            q = quotes[symbol]
            price = float(q['close'])
            change = float(q.get('percent_change', 0))
            
            color = "#0f0" if change >= 0 else "#f00"
            
            html += f"""
            <tr style="border-bottom: 1px solid #222;">
                <td style="padding: 10px;">{symbol}</td>
                <td style="padding: 10px;">{price:,.2f}</td>
                <td style="padding: 10px; color: {color};">{change:+.2f}%</td>
            </tr>
            """
            
        html += """
        </table>
        <p style="margin-top: 30px; font-size: 0.8em; color: #666;">
            Hinweis: 1 Call verbraucht 7/8 Minuten-Credits. <br>
            Nicht öfter als 1x pro Minute aktualisieren.
        </p>
    </body>
    </html>
    """
        
    except Exception as e:
        html += f"<p style='color: #f80;'>Limit erreicht oder API-Pause: Bitte in 60 Sek. neu laden.</p>"
    
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
