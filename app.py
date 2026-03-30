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
    results, prices = [], {}

    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="5d")
            if h.empty or len(h) < 2:
                continue

            p, prev = h['Close'].iloc[-1], h['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            prices[name] = p

            is_fx = "EURUSD" in sym
            is_copper = "HG=F" in sym
            is_oil = "CL=F" in sym

            # RVOL & Ampel
            rv_str = "N/A"
            al = "success"

            # Aktien / Indizes RVOL
            if not is_fx and not is_copper and not is_oil:
                h_v = t.history(period="1mo")
                cv, av = h_v['Volume'].iloc[-1], h_v['Volume'].iloc[-12:-2].mean()
                if cv == 0 or (av > 0 and cv/av > 50):
                    cv = h_v['Volume'].iloc[-2]
                rv = cv / av if av > 0 else 0
                rv_str = f"{rv:.2f}"
                al = "danger" if rv > 3.0 else "success"

            # Shortcut 2 Ampel für Öl
            if is_oil:
                if chg > 2:
                    al = "danger"
                elif chg > 0.5:
                    al = "warning"
                else:
                    al = "success"
                rv_str = "N/A"

            # Shortcut 2 Ampel für Kupfer
            if is_copper:
                if chg > 2:
                    al = "danger"
                elif chg > 0.5:
                    al = "warning"
                else:
                    al = "success"
                rv_str = "N/A"

            # =========================
            # Automatische Interpretation
            # =========================
            if is_copper or is_oil:
                if al == "danger":
                    interp = "stark auffällig"
                elif al == "warning":
                    interp = "leicht auffällig"
                else:
                    interp = "normal"
            else:  # Aktien / Indizes / Futures
                if chg > 2:
                    interp = "starker Anstieg"
                elif chg > 0.5:
                    interp = "leichter Anstieg"
                elif chg < -2:
                    interp = "starker Rückgang"
                elif chg < -0.5:
                    interp = "leichter Rückgang"
                else:
                    interp = "neutral"

            # =========================
            # Ampel-Farbe für echtes Icon
            # =========================
            if al == "danger":
                al_color = "red"
            elif al == "warning":
                al_color = "yellow"
            else:
                al_color = "green"

            results.append({
                "name": name,
                "p": f"{p:.4f}" if is_fx else f"{p
