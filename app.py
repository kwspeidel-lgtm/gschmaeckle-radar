import yfinance as yf
from datetime import datetime, timedelta

# Brent Öl Ticker
ticker = "BZ=F"

# Daten der letzten 5 Tage im 1-Stunden-Intervall (oder kleiner)
data = yf.download(ticker, period="5d", interval="1h")

# Filter für 08:00 Uhr (Beispiel)
# Hinweis: Achte auf die Zeitzone (Yahoo liefert oft UTC oder EST)
volume_today = data.iloc[-1]['Volume'] # Letzte verfügbare Bar
# Hier müsste eine Logik rein, die exakt den Zeitstempel von "gestern 08:00" sucht
