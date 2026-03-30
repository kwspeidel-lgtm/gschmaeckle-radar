from flask import Flask, render_template_string
import yfinance as yf
from time import time

app = Flask(__name__)

TICKERS = {
    "DAX (^GDAXI)": "^GDAXI",
    "S&P 500 (^GSPC)": "^GSPC",
    "Gold (GC=F)": "GC=F", 
    "Silber (SI=F)": "SI=F",
    "Kupfer (HG=F)": "HG=F",
    "Öl WTI (CL=F)": "CL=F",
    "Bitcoin (BTC-USD)": "BTC-USD",
    "EUR/USD (EURUSD=X)": "EURUSD=X"
}

CACHE = {"data": None, "time": 0}

def get_market_data():
    results, prices, extra = [], {}, {}

    for name, sym in TICKERS.items():
        try:
            t = yf.Ticker(sym)

            h = t.history(period="5d")
            if h.empty or len(h) < 2:
                continue

            p = h['Close'].iloc[-1]
            prev = h['Close'].iloc[-2]
            chg = ((p - prev) / prev) * 100
            prices[name] = p

            is_fx = "EURUSD" in sym
            rv_val = None

            if not is_fx:
                h_v = t.history(period="1mo")
                cv = h_v['Volume'].iloc[-1]
                av = h_v['Volume'].iloc[-12:-2].mean()

                if cv == 0 or (av > 0 and cv/av > 50):
                    cv = h_v['Volume'].iloc[-2]

                rv_val = cv / av if av > 0 else 0

            # wichtige Werte speichern für Algo
            if "Öl" in name:
                extra["oil_rvol"] = rv_val
                extra["oil_chg"] = chg
            if "Kupfer" in name:
                extra["copper_chg"] = chg
            if "S&P" in name:
                extra["spx_chg"] = chg

            results.append({
                "name": name,
                "p": f"{p:.4f}" if is_fx else f"{p:.2f}",
                "chg": f"{chg:+.2f}%",
                "c_val": chg,
                "rv": f"{rv_val:.2f}" if rv_val and not is_fx else "N/A",
                "al": "danger" if (rv_val and rv_val > 2) else "success"
            })

        except:
            continue

    # Ratio
    try:
        g = next(v for k,v in prices.items() if "Gold" in k)
        s = next(v for k,v in prices.items() if "Silber" in k)
        ratio = g / s
    except:
        ratio = None

    return results, ratio, extra


def get_cached():
    if time() - CACHE["time"] < 60:
        return CACHE["data"]

    data = get_market_data()
    CACHE["data"] = data
    CACHE["time"] = time()
    return data


# 🔥 SHORTCUT 2 ALGO ENGINE
def algo_signal(ratio, extra):
    score = 0

    oil_rvol = extra.get("oil_rvol", 0)
    oil_chg = extra.get("oil_chg", 0)
    copper = extra.get("copper_chg", 0)
    spx = extra.get("spx_chg", 0)

    # 1. Öl Volumen
    if oil_rvol and oil_rvol > 2:
        score += 1

    # 2. Ratio
    if ratio:
        if ratio > 85:
            score -= 1
        elif ratio < 75:
            score += 1

    # 3. S&P Richtung
    if spx > 0:
        score += 1
    else:
        score -= 1

    # Ergebnis
    if score >= 2:
        return "🟢 RISK ON"
    elif score <= -1:
        return "🔴 RISK OFF"
    else:
        return "🟡 NEUTRAL"


# 🔥 INSIDER FLOW
def insider_flow(extra, ratio):
    oil_rvol = extra.get("oil_rvol", 0)
    oil_chg = extra.get("oil_chg", 0)
    copper = extra.get("copper_chg", 0)

    flow = []

    if oil_rvol and oil_rvol > 2 and oil_chg > 0:
        flow.append("Öl Demand ↑")

    if copper < 0:
        flow.append("Growth ↓")

    if ratio and ratio > 85:
