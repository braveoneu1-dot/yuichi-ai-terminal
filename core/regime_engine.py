# =====================================================
# MARKET REGIME ENGINE
# =====================================================

import pandas as pd
from pathlib import Path
from datetime import datetime

# =====================================================
# REGIME HISTORY FILE
# =====================================================

REGIME_FILE = Path("data/regime_history.csv")

# =====================================================
# MARKET REGIME DETECTION
# =====================================================

def detect_market_regime(macro_changes):

    nasdaq = macro_changes.get("NASDAQ", 0)
    vix = macro_changes.get("VIX", 0)
    oil = macro_changes.get("OIL", 0)
    btc = macro_changes.get("BTC", 0)

    score = 0
    drivers = []

    # =====================================================
    # NASDAQ
    # =====================================================

    if nasdaq > 0.5:
        score += 2
        drivers.append("Tech strength")

    elif nasdaq < -0.5:
        score -= 2
        drivers.append("Tech weakness")

    # =====================================================
    # VIX
    # =====================================================

    if vix > 20:
        score -= 2
        drivers.append("Fear rising")

    elif vix < 15:
        score += 1
        drivers.append("Fear easing")

    # =====================================================
    # OIL
    # =====================================================

    if oil > 2:
        score -= 1
        drivers.append("Oil spike")

    elif oil < -4:
        score += 1
        drivers.append("Oil collapse easing inflation fears")

    # =====================================================
    # BTC
    # =====================================================

    if btc > 0.5:
        score += 1
        drivers.append("Crypto strength")

    elif btc < -1:
        score -= 1
        drivers.append("Crypto weakness")

    # =====================================================
    # FINAL REGIME
    # =====================================================

    confidence = min(abs(score) / 5, 1)

    if score >= 3:

        regime = {
            "name": "RISK_ON",
            "emotion": "greed",
            "color": "#22c55e",
            "confidence": confidence,
            "drivers": drivers
        }

    elif score <= -3:

        regime = {
            "name": "RISK_OFF",
            "emotion": "fear",
            "color": "#ef4444",
            "confidence": confidence,
            "drivers": drivers
        }

    else:

        regime = {
            "name": "NEUTRAL",
            "emotion": "uncertain",
            "color": "#facc15",
            "confidence": confidence,
            "drivers": drivers
        }

    return regime


# =====================================================
# SAVE REGIME HISTORY
# =====================================================

def save_regime_history(regime):

    REGIME_FILE.parent.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    new_row = pd.DataFrame([
        {
            "date": today,
            "regime": regime["name"]
        }
    ])

    if REGIME_FILE.exists():

        history = pd.read_csv(REGIME_FILE)

        if today not in history["date"].astype(str).values:

            history = pd.concat(
                [history, new_row],
                ignore_index=True
            )

            history.to_csv(REGIME_FILE, index=False)

    else:

        new_row.to_csv(REGIME_FILE, index=False)


# =====================================================
# LOAD REGIME HISTORY
# =====================================================

def load_regime_history():

    if REGIME_FILE.exists():

        return pd.read_csv(REGIME_FILE)

    return pd.DataFrame(
        columns=["date", "regime"]
    )