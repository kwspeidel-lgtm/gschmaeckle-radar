from flask import Flask, render_template_string
import yfinance as yf
from datetime import datetime
import pytz

app = Flask(__name__)

TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "Euro Stoxx 50 (^STOXX50E)": "^STOXX50E",
    "S&P 500 (^GSPC)": "^GSPC",
    "Gold (GC=F)": "GC=F", 
    "Silber (SI=F)": "SI=F", 
    "Öl WTI (CL=F)": "CL=F", 
    "EUR/USD (EURUSD=X)": "EURUSD=X"
}
RVOL_LIMIT = 3.0

def get_market_data():
    results = []
    prices = {}
    # Zeitstempel für Berlin
    now = datetime.now(pytz.timezone('Europe/Berlin')).strftime('%H:%M:%S')
    
    for name, sym in TICKERS.items():
        try:
            ticker = yf.Ticker(sym)
            # 5 Tage laden, um sicher den letzten Schlusskurs zu haben
            h = ticker.history(period="5d")
            if len(h) < 2: continue
            
            last_price = h['Close'].iloc[-1]
            prev_close = h['Close'].iloc[-2] # Der offizielle Schlusskurs von gestern
            change_pct = ((last_price - prev_close) / prev_close) * 100
            
            # RVOL Logik
            curr_v = h['Volume'].iloc[-1]
            avg_v = h['Volume'].iloc[-5:-1].mean()
            
            is_fx = "EURUSD" in sym
            rvol = curr_v / avg_v if (avg_v > 0 and not is_fx) else 0
            
            prices[name] = last_price
            results.append({
                "name": name,
                "price": f"{last_price:.4f}" if is_fx else f"{last_price:.2f}",
                "change": f"{change_pct:+.2f}%",
                "change_val": change_pct,
                "rvol": f"{rvol:.2f}" if (not is_fx and rvol > 0) else "",
                "is_fx": is_fx,
                "alert": "danger" if (rvol > RVOL_LIMIT) else "success"
            })
        except:
            results.append({"name": name, "price": "Fehler", "change": "0%", "change_val": 0, "rvol": "", "alert": "secondary"})
    
    try:
        ratio = f"{prices['Gold (GC=F)'] / prices['Silber (SI=F)']:.2f}"
    except:
        ratio = "N/A"
        
    return results, ratio, now

HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gschmäckle Radar v1.9</title><meta name="mobile-web-app-capable" content="yes">
<meta http-equiv="refresh" content="60"> <link rel="icon" href="https://cdn-icons-png.flaticon.com/512/1995/1995531.png">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
    body{background:#0a0a0a;color:#ffffff;font-family:sans-serif;} 
    .neon{color:#39ff14;text-shadow:0 0 5px #39ff14;}
    .card{background:#161616;border-radius:12px;padding:12px;margin-bottom:10px;border:1px solid #333;}
    .ratio-box{border: 1px solid #444; padding: 10px; border-radius: 8px; margin-bottom: 15px; background: #111;}
    .border-danger{border:2px solid #ff3131!important;box-shadow:0 0 10px #ff3131;}
    .border-success{border:1px solid #222!important;}
    .up { color: #00d4ff; } .down { color: #ff3131; }
    .label-text{color: #666; font-size: 0.7rem; text-transform: uppercase;}
    .price-text{font-size: 1.1rem; font-weight: bold; color: #eee;}
    .update-text { font-size: 0.7rem; color: #444; margin-bottom: 10px; }
    .disclaimer { font-size: 0.6rem; color: #333; padding: 15px; border-top: 1px solid #111; margin-top: 10px; line-height: 1.2; }
</style></head>
<body>
<div class="container py-2">
    <h2 class="text-center neon mb-2">Gschmäckle Radar v1.9 🚀</h2>
    <div class="text-center update-text">Letztes Update: {{ now }} (Auto-Refresh 60s)</div>
    
    <div class="text-center ratio-box">
        <small class="label-text">Gold/Silber Ratio</small><br><span class="h4 neon">{{ ratio }}</span>
    </div>

    <div class="row g-2">
        {% for a in assets %}
        <div class="col-12 col-md-6">
            <div class="card border-{{a.alert}}">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <h6 class="mb-0 fw-bold" style="color: #39ff14; font-size: 0.9rem;">{{a.name}}</h6>
                    <span class="{% if a.change_val >= 0 %}up{% else %}down{% endif %} fw-bold small">{{a.change}}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="label-text">Preis</span><span class="price-text">{{a.price}}</span>
                </div>
                {% if not a.is_fx %}
                <div class="d-flex justify-content-between align-items-center">
                    <span class="label-text">RVOL (Insider)</span><strong class="text-{{a.alert}} small">{{a.rvol}}</strong>
                </div>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="disclaimer">
        <strong>RISIKOHINWEIS:</strong> Informationen basieren auf verzögerten Yahoo-Daten. RVOL ist ein statistisches Maß für Volumen-Abweichungen zum Vortages-Schnitt. Keine Anlageberatung. Haftung für Datenfehler ausgeschlossen.
    </div>
</div>
</body></html>
