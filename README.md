# Gschmäckle App - Insider Update 2026

Diese Version ist auf **Twelve Data** optimiert und dient zum Aufspüren von Insider-Bewegungen mittels **RVOL-Analyse**.

## Installation
1. Stelle sicher, dass Python installiert ist.
2. Installiere die Anforderungen:
   `pip install -r requirements.txt`

## Nutzung
Starte die App einfach per Terminal:
`python app.py`

## Features
- **Echtzeit-Kurse:** Direkt über Twelve Data API.
- **RVOL (Relative Volume):** Vergleicht das aktuelle Volumen mit der exakt gleichen Uhrzeit des letzten Börsentages (umgeht Wochenenden automatisch).
- **Insider-Symbole:** Überwacht WTI, Brent, Gold, Silber, DXY, VIX und den Bund-Future.
- **On-Demand:** Verbraucht nur Credits, wenn die App gestartet wird.

**Key:** 0c4ce2fc... (direkt in app.py hinterlegt)
