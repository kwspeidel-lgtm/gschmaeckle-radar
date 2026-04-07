import pandas as pd
from twelvedata import TDClient
import time
from datetime import datetime, timedelta

# --- KONFIGURATION ---
API_KEY = "0c4ce2fcaffa4f1592e012cfef854161"
# Deine 10 Insider-Symbole (ETH durch LCO/USD ersetzt)
SYMBOLS = ["BTC/USD", "WTI/USD", "LCO/USD", "XAU/USD", "XAG/USD", "DXY", "VIX", "DAX", "SPX", "FGBL"]

def get_gschmaeckle_update():
    td = TDClient(apikey=API_KEY)
    
    print(f"\n=== GSCHMÄCKLE INSIDER-CHECK ({datetime.now().strftime('%H:%M:%S')}) ===")
    print(f"{'Asset':<10} | {'Preis':<10} | {'RVOL':<8} | {'Status'}")
    print("-" * 50)

    try:
        # 1. Aktuelle Quoten (Batch-Request für Effizienz)
        quotes = td.quote(symbol=SYMBOLS).as_json()
        
        # 2. Historische Daten für RVOL (Letzte 5000 Minuten für Wochenend-Check)
        # Wir brauchen ein breites Fenster, um den letzten Börsentag sicher zu finden
        ts_data = td.time_series(symbol=SYMBOLS, interval="1min", outputsize=5000).as_json()

        now = datetime.now()
        current_time_str = now.strftime("%H:%M")

        for symbol in SYMBOLS:
            # Daten für dieses Symbol extrahieren
            q = quotes[symbol] if len(SYMBOLS) > 1 else quotes
            price = float(q['close'])
            vol_today = float(q['volume'])
            
            # RVOL Logik: Suche gleichen Zeitpunkt am letzten Handelstag
            history = ts_data[symbol]['values'] if len(SYMBOLS) > 1 else ts_data['values']
            rvol = 1.0
            status = "Normal"
            
            # Finde den ersten Datenpunkt, der NICHT von heute ist, aber die gleiche Uhrzeit hat
            ref_bar = None
            today_str = now.strftime("%Y-%m-%d")
            
            for bar in history:
                if today_str not in bar['datetime'] and current_time_str in bar['datetime']:
                    ref_bar = bar
                    break
            
            if ref_bar:
                vol_ref = float(ref_bar['volume'])
                if vol_ref > 0:
                    rvol = vol_today / vol_ref
                
                # Insider-Trigger (Shortcut 2 / RVOL > 3)
                if rvol > 3.0:
                    status = "⚠️ INSIDER ALARM!"
                elif rvol > 2.0:
                    status = "⚡ Erhöht"

            print(f"{symbol:<10} | {price:<10.2f} | {rvol:<8.2f} | {status}")

    except Exception as e:
        print(f"Fehler beim Abruf: {e}")

if __name__ == "__main__":
    # Die App führt den Check einmal aus (On-Demand wie gewünscht)
    get_gschmaeckle_update()
