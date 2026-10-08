"""Data loading (CSV -> SQLite), cleaning and preprocessing report."""
import hashlib
import os
import sqlite3
import threading

import numpy as np
import pandas as pd
from sklearn.feature_selection import f_classif
from sklearn.preprocessing import StandardScaler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "smart_campus_energy_analytics_8000.csv")
DB_PATH = os.path.join(BASE_DIR, "database", "campus_energy.db")
TABLE = "campus_energy"

# Feature sets shared by the ML modules (targets / derived columns are never included)
NUM_CLS = ["temperature_c", "humidity_pct", "occupancy_pct", "hvac_usage_pct", "lighting_usage_pct", "hour"]
CAT_CLS = ["building_type", "temperature_level", "occupancy_level"]
NUM_REG = ["temperature_c", "humidity_pct", "occupancy_pct", "hvac_usage_pct", "lighting_usage_pct", "hour",
           "floor_area_sqft"]
CAT_REG = ["building_type"]
NUM_CLU = ["temperature_c", "occupancy_pct", "hvac_usage_pct", "lighting_usage_pct", "energy_consumption_kwh"]

NUMERIC_COLS = ["floor_area_sqft", "floor_count", "hour", "day_of_week", "month", "is_weekend", "temperature_c",
                "humidity_pct", "occupancy_pct", "hvac_usage_pct", "lighting_usage_pct",
                "energy_consumption_kwh", "estimated_cost_inr", "co2_kg", "anomaly_flag"]
CATEGORICAL_COLS = ["building_id", "building_name", "building_type", "occupancy_level", "temperature_level",
                    "energy_category"]

_lock = threading.RLock()
_cache = {}


# --------------------------------------------------------------- database
def _csv_rows():
    with open(DATA_PATH, "rb") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def init_db():
    """Import the CSV into SQLite once. Re-running never duplicates rows."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _lock, sqlite3.connect(DB_PATH) as con:
        exists = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE,)).fetchone()
        n = con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] if exists else 0
        if n > 0 and n == _csv_rows():
            return {"imported": False, "rows": n}
        raw = pd.read_csv(DATA_PATH)
        raw.to_sql(TABLE, con, if_exists="replace", index=False)  # replace => no duplicates on re-import
        for col in ("building_name", "building_type", "month", "energy_category", "hour"):
            con.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON {TABLE}({col})")
        _cache.clear()
        return {"imported": True, "rows": len(raw)}


def load_raw():
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query(f"SELECT * FROM {TABLE}", con)


def dataset_signature():
    with _lock:
        if "sig" not in _cache:
            with open(DATA_PATH, "rb") as fh:
                _cache["sig"] = hashlib.md5(fh.read()).hexdigest()
        return _cache["sig"]


# --------------------------------------------------------------- cleaning
def _clean(raw):
    df = raw.copy()
    log = {}
    log["duplicates_removed"] = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)

    filled = {}
    for col in df.columns:
        n = int(df[col].isna().sum())
        if n == 0:
            continue
        if col in NUMERIC_COLS:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())
            filled[col] = f"{n} -> median"
        elif col != "timestamp":
            df[col] = df[col].fillna(df[col].mode().iloc[0])
            filled[col] = f"{n} -> mode"
    log["missing_filled"] = filled

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_ts = int(df["timestamp"].isna().sum())
    if bad_ts:
        df = df.dropna(subset=["timestamp"]).reset_index(drop=True)
    log["invalid_timestamps_dropped"] = bad_ts
    return df, log


def get_clean_df():
    with _lock:
        if "clean" not in _cache:
            init_db()
            _cache["clean"], _cache["clean_log"] = _clean(load_raw())
        return _cache["clean"]


def get_clean_log():
    get_clean_df()
    return _cache["clean_log"]


# --------------------------------------------------------------- report
def preprocessing_report():
    raw = load_raw()
    clean, log = _clean(raw)

    miss = raw.isna().sum()
    before = {
        "rows": int(len(raw)),
        "columns": int(raw.shape[1]),
        "missing_total": int(miss.sum()),
        "duplicates": int(raw.duplicated().sum()),
    }
    after = {
        "rows": int(len(clean)),
        "columns": int(clean.shape[1]),
        "missing_total": int(clean.isna().sum().sum()),
        "duplicates": int(clean.duplicated().sum()),
    }
    missing_by_col = [{"column": c, "missing": int(v), "pct": round(v / len(raw) * 100, 2)}
                      for c, v in miss.items() if v > 0]

    # timestamp conversion
    raw_ts_type = str(raw["timestamp"].dtype)
    ts = {"before": raw_ts_type, "after": str(clean["timestamp"].dtype),
          "min": str(clean["timestamp"].min()), "max": str(clean["timestamp"].max())}

    # categorical encoding (one-hot for features, ordinal for the class label)
    encoding = []
    for col in CAT_CLS:
        cats = sorted(clean[col].unique().tolist())
        encoding.append({"column": col, "method": "One-hot", "categories": cats, "new_columns": len(cats)})
    order = {"Low": 0, "Medium": 1, "High": 2}
    present = [c for c in order if c in set(clean["energy_category"])]
    encoding.append({"column": "energy_category (target)", "method": "Label / ordinal",
                     "categories": [f"{c} = {order[c]}" for c in present], "new_columns": 1})

    # scaling (z-score) of the numeric classification/regression/clustering features
    scale_cols = list(dict.fromkeys(NUM_CLS + NUM_REG + NUM_CLU))
    scaled = StandardScaler().fit_transform(clean[scale_cols])
    scaling = [{"column": c, "mean_before": round(float(clean[c].mean()), 3), "std_before": round(float(clean[c].std()), 3),
                "mean_after": round(float(scaled[:, i].mean()), 3), "std_after": round(float(scaled[:, i].std()), 3)}
               for i, c in enumerate(scale_cols)]

    # feature selection: correlation with energy (regression) and ANOVA F-score vs class (classification)
    corr = clean[NUM_REG].corrwith(clean["energy_consumption_kwh"])
    cls_df = clean[NUM_CLS]
    f_scores, _ = f_classif(cls_df, clean["energy_category"])
    selection = []
    for c in NUM_REG:
        selection.append({
            "feature": c,
            "corr_with_energy": round(float(corr[c]), 3),
            "f_score_vs_category": round(float(f_scores[NUM_CLS.index(c)]), 1) if c in NUM_CLS else None,
            "used_in": ", ".join(x for x, cols in (("Classification", NUM_CLS), ("Regression", NUM_REG)) if c in cols),
        })
    for c in CAT_CLS:
        selection.append({"feature": c, "corr_with_energy": None, "f_score_vs_category": None,
                          "used_in": ", ".join(x for x, cols in (("Classification", CAT_CLS), ("Regression", CAT_REG))
                                               if c in cols) or "-"})
    excluded = [
        {"column": "energy_consumption_kwh", "reason": "Regression target / would leak the class label"},
        {"column": "energy_category", "reason": "Classification target"},
        {"column": "estimated_cost_inr", "reason": "Derived from energy (target leakage)"},
        {"column": "co2_kg", "reason": "Derived from energy (target leakage)"},
        {"column": "anomaly_flag", "reason": "Not used (no anomaly module in this project)"},
        {"column": "building_id / building_name / timestamp", "reason": "Identifiers - no predictive meaning"},
    ]

    preview_cols = ["building_name", "hour", "temperature_c", "occupancy_pct", "hvac_usage_pct", "energy_consumption_kwh"]
    preview = clean[preview_cols].head(5)
    scaled_prev = pd.DataFrame(scaled[:5], columns=scale_cols)[["temperature_c", "occupancy_pct", "hvac_usage_pct",
                                                                "lighting_usage_pct"]].round(3)
    steps = [
        {"step": "Load CSV into SQLite", "result": f"{before['rows']:,} rows imported into table '{TABLE}'"},
        {"step": "Duplicate removal", "result": f"{log['duplicates_removed']} duplicate rows removed"},
        {"step": "Missing value handling", "result": ("; ".join(f"{k}: {v}" for k, v in log["missing_filled"].items())
                                                      or "No missing values found")},
        {"step": "Timestamp conversion", "result": f"{raw_ts_type} -> {ts['after']}"},
        {"step": "Categorical encoding", "result": f"One-hot for {len(CAT_CLS)} features, ordinal for target"},
        {"step": "Numerical scaling", "result": f"Z-score on {len(scale_cols)} numeric columns"},
        {"step": "Feature selection", "result": "Target-derived columns and identifiers excluded"},
    ]
    return {
        "before": before, "after": after, "steps": steps, "missing_by_col": missing_by_col, "timestamp": ts,
        "encoding": encoding, "scaling": scaling, "selection": selection, "excluded": excluded,
        "preview": preview.assign(hour=preview["hour"].astype(int)).to_dict("records"),
        "scaled_preview": scaled_prev.to_dict("records"),
    }
