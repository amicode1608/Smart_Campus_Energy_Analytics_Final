"""Random Forest regression predicting energy_consumption_kwh."""
import os
import threading

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .preprocessing import BASE_DIR, CAT_REG, NUM_REG, dataset_signature, get_clean_df

MODEL_PATH = os.path.join(BASE_DIR, "models", "regression_model.pkl")
COST_PER_KWH = 8.5   # INR
CO2_PER_KWH = 0.71   # kg
_lock = threading.RLock()
_state = None


def _train(df):
    X, y = df[NUM_REG + CAT_REG], df["energy_consumption_kwh"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    prep = ColumnTransformer([("num", "passthrough", NUM_REG),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_REG)])
    rf = RandomForestRegressor(n_estimators=120, max_depth=14, min_samples_leaf=3, n_jobs=-1, random_state=42)
    pipe = Pipeline([("prep", prep), ("rf", rf)]).fit(X_tr, y_tr)
    pred = pipe.predict(X_te)
    resid = y_te.to_numpy() - pred

    names = list(pipe.named_steps["prep"].get_feature_names_out())
    imp = {}
    for nm, v in zip(names, rf.feature_importances_):
        key = "building_type" if nm.startswith("cat__building_type") else nm.replace("num__", "")
        imp[key] = imp.get(key, 0.0) + float(v)
    imp = dict(sorted(imp.items(), key=lambda kv: -kv[1]))

    rng = np.random.default_rng(42)
    idx = rng.choice(len(y_te), size=min(500, len(y_te)), replace=False)
    counts, edges = np.histogram(resid, bins=20)
    t = pd.DataFrame({"hour": X_te["hour"].to_numpy(), "actual": y_te.to_numpy(), "pred": pred}).groupby("hour").mean()

    return {
        "signature": dataset_signature(),
        "pipeline": pipe,
        "metrics": {
            "mae": float(mean_absolute_error(y_te, pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_te, pred))),
            "r2": float(r2_score(y_te, pred)),
            "train_size": int(len(X_tr)), "test_size": int(len(X_te)),
            "mean_energy": float(y.mean()),
            "scatter": {"actual": np.round(y_te.to_numpy()[idx], 2).tolist(), "predicted": np.round(pred[idx], 2).tolist()},
            "residuals": {"labels": [f"{(edges[i] + edges[i + 1]) / 2:.1f}" for i in range(len(counts))],
                          "counts": counts.tolist()},
            "trend": {"labels": [f"{int(h):02d}:00" for h in t.index], "actual": t["actual"].round(2).tolist(),
                      "predicted": t["pred"].round(2).tolist()},
            "importance": {"labels": list(imp), "values": [round(v, 4) for v in imp.values()]},
        },
        "options": {
            "building_type": sorted(df["building_type"].unique().tolist()),
            "floor_area": df.groupby("building_type")["floor_area_sqft"].median().to_dict(),
            "ranges": {c: [float(df[c].min()), float(df[c].max()), round(float(df[c].mean()), 1)] for c in NUM_REG},
        },
    }


def get_state():
    global _state
    with _lock:
        if _state is not None:
            return _state
        if os.path.exists(MODEL_PATH):
            try:
                saved = joblib.load(MODEL_PATH)
                if saved.get("signature") == dataset_signature():
                    _state = saved
                    return _state
            except Exception:
                pass
        _state = _train(get_clean_df())
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(_state, MODEL_PATH, compress=3)
        return _state


def metrics():
    s = get_state()
    return {"model": "Random Forest Regressor", "features": NUM_REG + CAT_REG, **s["metrics"], "options": s["options"]}


def predict(payload):
    s = get_state()
    row = {}
    for col in NUM_REG:
        try:
            val = float(payload.get(col))
        except (TypeError, ValueError):
            raise ValueError(f"'{col}' must be a number.")
        if not np.isfinite(val):
            raise ValueError(f"'{col}' must be a finite number.")
        row[col] = val
    if row["floor_area_sqft"] <= 0:
        raise ValueError("Floor area must be greater than 0.")
    if not 0 <= row["hour"] <= 23:
        raise ValueError("Hour must be between 0 and 23.")
    for col in ("humidity_pct", "occupancy_pct", "hvac_usage_pct", "lighting_usage_pct"):
        if not 0 <= row[col] <= 100:
            raise ValueError(f"'{col}' must be between 0 and 100.")
    if payload.get("building_type") not in s["options"]["building_type"]:
        raise ValueError("Unknown building type.")
    row["building_type"] = payload["building_type"]
    kwh = max(float(s["pipeline"].predict(pd.DataFrame([row])[NUM_REG + CAT_REG])[0]), 0.0)
    return {"energy_kwh": round(kwh, 2), "cost_inr": round(kwh * COST_PER_KWH, 2), "co2_kg": round(kwh * CO2_PER_KWH, 2)}
