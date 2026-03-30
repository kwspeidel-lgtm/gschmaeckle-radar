from flask import Flask, render_template_string
import yfinance as yf

app = Flask(__name__)

# =========================
# Tickerliste
# =========================
TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "Euro Stoxx 50 (^STOXX50E)": "^STOXX50E",
    "S&P 500 (^GSPC)": "^GSPC",
    "Gold (GC=F)": "GC=F",
    "Silber (SI=F)": "SI=F",
    "Kupfer (HG=F)": "HG=F",
    "Öl WTI (CL=F)": "CL=F",
    "EUR/USD (EURUSD=X)": "EURUSD=X",
    "Bitcoin (BTC-USD)": "BTC-USD"
}

# =========================
# Daten abholen + Interpretation + Ampel-Farbe
# =========================
def get_market_data():
    results, prices = [], []

    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if h.empty or len(h) < 2:
                continue

            p, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            prices.append((name, p))

            is_fx = "EURUSD" in sym
            is_copper = "HG=F" in sym
            is_oil = "CL=F" in sym

            # RVOL berechnen, nur wenn sinnvoll
            rv_str = "N/A"
            rvol = 0
            if not is_fx and not is_copper and not is_oil:
                h_v = t.history(period="1mo")
                cv, av = h_v['Volume'].iloc[-1], h_v['Volume'].iloc[-12:-2].mean()
                if cv == 0 or (av > 0 and cv/av > 50):
                    cv = h_v['Volume'].iloc[-2]
                rvol = cv / av if av > 0 else 0
                rv_str = f"{rvol:.2f}"

            # Ampel-Logik
            al = "success"
            if not is_fx and not is_copper and not is_oil and rvol > 3.0:
                al = "danger"

            # Shortcut 2 Ampel für Öl & Kupfer
            if is_oil or is_copper:
                if chg > 2:
                    al =
