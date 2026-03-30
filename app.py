
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

# --- KONFIGURATION & LOGIK ---
# Liste der zu scannenden Ticker
TICKERS = {
    "Gold (GC=F)": "GC=F",
    "Silber (SI=F)": "SI=F",
    "Öl WTI (CL=F)": "CL=F",
    "Öl Brent (BZ=F)": "BZ=F",
    "S&P 500 (^GSPC)": "^GSPC"
}

# Grenzwert für den Gschmäckle-Alarm
RVOL_THRESHOLD = 3.0

# Ziel-Ratio für Gold-Silber (nur zur Anzeige)
GOLD_SILVER_TARGET = 64.41

def get_asset_data():
    """
    Holt Daten für alle Assets, berechnet RVOL und implementiert Weekend/Zero-Fixes.
    """
    results = []
    
    # Heutiges Datum und Datum vor 15 Tagen (um genug Daten für den 10-Tage-Schnitt zu haben)
    today = datetime.now()
    start_date = today - timedelta(days=15)
    
    for name, ticker_symbol in TICKERS.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Versuche, die Daten der letzten 15 Tage zu holen
            hist = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'))
            
            # Weekend-Fix: Wenn heute (z.B. Sonntag) keine Daten da sind, nimm die vom letzten verfügbaren Tag
            if hist.empty or len(hist) < 2:
                # Versuche, Daten vom Vortag zu holen (z.B. Freitagsschluss am Samstag/Sonntag)
                yesterday = today - timedelta(days=1)
                hist = ticker.history(start=(yesterday - timedelta(days=15)).strftime('%Y-%m-%d'), end=yesterday.strftime('%Y-%m-%d'))
            
            # Falls immer noch leer, überspringe dieses Asset
            if hist.empty or len(hist) < 1:
                results.append({"name": name, "status": "error", "message": "N/A (No Data)"})
                continue

            # --- Berechnung von RVOL & Ampel ---
            # Aktuelles Volumen
            current_volume = hist['Volume'].iloc[-1]
            
            # Berechnung des 10-Tage-Schnitts (ohne das heutige Volumen)
            if len(hist) > 10:
                avg_10d_volume = hist['Volume'].iloc[-11:-1].mean()
            elif len(hist) > 1:
                 avg_10d_volume = hist['Volume'].iloc[:-1].mean()
            else:
                avg_10d_volume = 0 # Division-by-Zero-Schutz

            # Division-by-Zero-Schutz für RVOL-Berechnung
            if avg_10d_volume > 0:
                rvol = current_volume / avg_10d_volume
            else:
                rvol = 0
            
            # Gschmäckle-Alarm: RVOL > 3.0
            alert = "danger" if rvol > RVOL_THRESHOLD else "safe"
            
            # Stimmung (Panik/Gier) - Sehr simple Logik basierend auf RVOL
            sentiment = "Panik/Gier (Aktiv!)" if rvol > RVOL_THRESHOLD else "Ruhig (Normal)"
            sentiment_color = "danger" if rvol > RVOL_THRESHOLD else "success"

            # Preisdaten (falls verfügbar)
            price = hist['Close'].iloc[-1]
            # Für Silber den Preisbereich beachten (ca. 70 USD)
            if ticker_symbol == "SI=F" and price > 100:
                 price_msg = f"{price:.2f} USD (Bereich checken!)"
            else:
                 price_msg = f"{price:.2f} USD"

            results.append({
                "name": name,
                "status": "ok",
                "price": price_msg,
                "rvol": f"{rvol:.2f}",
                "avg_vol": int(avg_10d_volume),
                "alert": alert,
                "sentiment": sentiment,
                "sentiment_color": sentiment_color
            })

        except Exception as e:
            # Fehlerbehandlung: Wenn ein Asset nicht abgerufen werden kann
            results.append({"name": name, "status": "error", "message": str(e)})

    return results

def get_market_analysis(asset_data):
    """
    Berechnet Gold-Silber-Ratio und Brent-WTI-Spread.
    """
    analysis = {}
    
    # Gold-Silber-Ratio berechnen
    gold = next((a for a in asset_data if "Gold" in a["name"]), None)
    silber = next((a for a in asset_data if "Silber" in a["name"]), None)
    
    if gold and silber and gold["status"] == "ok" and silber["status"] == "ok":
        g_price = float(gold["price"].split(" ")[0])
        s_price = float(silber["price"].split(" ")[0])
        if s_price > 0:
            ratio = g_price / s_price
            analysis["ratio"] = f"{ratio:.2f}"
            analysis["ratio_target"] = f"{GOLD_SILVER_TARGET}"
        else:
            analysis["ratio"] = "Error"
    else:
        analysis["ratio"] = "N/A"
        
    # Öl-Spread (Brent/WTI) berechnen
    brent = next((a for a in asset_data if "Brent" in a["name"]), None)
    wti = next((a for a in asset_data if "WTI" in a["name"]), None)
    
    if brent and wti and brent["status"] == "ok" and wti["status"] == "ok":
        b_price = float(brent["price"].split(" ")[0])
        w_price = float(wti["price"].split(" ")[0])
        spread = b_price - w_price
        analysis["spread"] = f"{spread:.2f} USD"
    else:
        analysis["spread"] = "N/A"
        
    return analysis


# --- HTML TEMPLATE (IM CODE INTEGRIERT) ---
# Dark Mode, Neon-Akzente, Mobile-First
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Gschmäckle Radar v1.0</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --neon-green: #39ff14;
            --neon-red: #ff3131;
            --neon-blue: #00f7ff;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Courier New', Courier, monospace; /* Ticker-Feeling */
        }

        h1 {
            color: var(--neon-green);
            text-shadow: 0 0 10px var(--neon-green);
            text-align: center;
            margin-top: 20px;
        }

        .scanner-card {
            background-color: var(--card-bg);
            border: 2px solid var(--text-color);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .scanner-card:hover {
            transform: scale(1.02);
            box-shadow: 0 0 15px var(--text-color);
        }

        /* Gschmäckle-Alarm (Rot) */
        .scanner-card.border-danger {
            border-color: var(--neon-red) !important;
            box-shadow: 0 0 20px var(--neon-red);
        }

        /* Normal (Grün) */
        .scanner-card.border-success {
            border-color: var(--neon-green) !important;
            box-shadow: 0 0 10px var(--neon-green);
        }

        .card-title {
            color: var(--neon-blue);
            font-weight: bold;
        }

        .meta-analysis {
            background-color: #1a1a1a;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 30px;
        }

        .meta-title {
            color: var(--neon-blue);
            font-size: 1.2rem;
            text-transform: uppercase;
        }

        footer {
            background-color: #0d0d0d;
            padding: 20px;
            margin-top: 40px;
            font-size: 0.8rem;
            color: #888;
            text-align: center;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Gschmäckle Radar v1.0 🚀</h1>
    <p class="text-center text-muted">Echtzeit Asset-Scanner</p>

    <div class="meta-analysis row">
        <div class="col-md-6 text-center">
            <p class="meta-title">Gold-Silber Ratio</p>
            <p class="h3">{{ analysis.ratio }} <small class="text-muted">(Ziel: {{ analysis.ratio_target }})</small></p>
        </div>
        <div class="col-md-6 text-center">
            <p class="meta-title">Öl-Spread (Brent/WTI)</p>
            <p class="h3">{{ analysis.spread }}</p>
        </div>
    </div>

    <div class="row">
        {% for asset in assets %}
        <div class="col-md-6 col-lg-4">
            <div class="scanner-card border border-{{ asset.alert }}">
                <div class="card-body">
                    <h5 class="card-title text-center">{{ asset.name }}</h5>
                    <hr>
                    {% if asset.status == "ok" %}
                    <p>Preis: <strong>{{ asset.price }}</strong></p>
                    <p>RVOL: <strong class="text-{{ asset.alert }} h4">{{ asset.rvol }}</strong> (Schnitt 10T: {{ asset.avg_vol }})</p>
                    <p>Stimmung: <span class="badge bg-{{ asset.sentiment_color }}">{{ asset.sentiment }}</span></p>
                    {% else %}
                    <p class="text-danger">Fehler: {{ asset.message }}</p>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endfor %}
    </div>

</div>

<footer>
    Hinweis: Das 'Gschmäckle Radar' zeigt algorithmische Volumen-Anomalien. Daten verzögert. Keine Anlageberatung. Nutzung auf eigene Gefahr.
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# --- ROUTES ---
@app.route("/")
def home():
    # Daten für alle Assets holen
    assets_data = get_asset_data()
    # Gold/Silber & Öl Analyse berechnen
    analysis_data = get_market_analysis(assets_data)
    
    # HTML mit den echten Daten rendern
    return render_template_string(HTML_TEMPLATE, assets=assets_data, analysis=analysis_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
