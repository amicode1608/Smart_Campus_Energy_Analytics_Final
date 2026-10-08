"""J48-style decision tree (entropy criterion) predicting energy_category."""
import os
import threading

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from .preprocessing import BASE_DIR, CAT_CLS, NUM_CLS, dataset_signature, get_clean_df

MODEL_PATH = os.path.join(BASE_DIR, "models", "classification_model.pkl")
CLASS_ORDER = ["Low", "Medium", "High"]
TREE_VIZ_DEPTH = 3
_lock = threading.RLock()
_state = None


def _readable(name):
    """'cat__building_type_Library' -> ('building_type', 'Library'); numeric -> (name, None)."""
    if name.startswith("cat__"):
        body = name[5:]
        for col in CAT_CLS:
            if body.startswith(col + "_"):
                return col, body[len(col) + 1:]
    return name.replace("num__", ""), None


def _tree_json(tree, names, classes, node=0, depth=0):
    t = tree.tree_
    n = {"samples": int(t.n_node_samples[node]), "label": classes[int(np.argmax(t.value[node][0]))],
         "entropy": round(float(t.impurity[node]), 3)}
    if t.children_left[node] != -1:
        col, val = _readable(names[t.feature[node]])
        if depth >= TREE_VIZ_DEPTH:
            n["truncated"] = True
            return n
        if val is None:
            n["split"], n["left_label"], n["right_label"] = f"{col} ≤ {t.threshold[node]:.2f}", "yes", "no"
        else:  # one-hot column: <= 0.5 means "not this category"
            n["split"], n["left_label"], n["right_label"] = f"{col} = {val}", "no", "yes"
        n["left"] = _tree_json(tree, names, classes, t.children_left[node], depth + 1)
        n["right"] = _tree_json(tree, names, classes, t.children_right[node], depth + 1)
    return n


def _train(df):
    X, y = df[NUM_CLS + CAT_CLS], df["energy_category"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    prep = ColumnTransformer([("num", "passthrough", NUM_CLS),
                              ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_CLS)])
    tree = DecisionTreeClassifier(criterion="entropy", max_depth=6, min_samples_leaf=10, random_state=42)
    pipe = Pipeline([("prep", prep), ("tree", tree)]).fit(X_tr, y_tr)

    classes = [c for c in CLASS_ORDER if c in set(y)]
    pred = pipe.predict(X_te)
    p, r, f, _ = precision_recall_fscore_support(y_te, pred, average="weighted", zero_division=0)
    pc, rc, fc, sc = precision_recall_fscore_support(y_te, pred, labels=classes, zero_division=0)
    names = list(pipe.named_steps["prep"].get_feature_names_out())

    importance = {}
    for nm, imp in zip(names, tree.feature_importances_):
        col = _readable(nm)[0]
        importance[col] = importance.get(col, 0.0) + float(imp)
    importance = dict(sorted(importance.items(), key=lambda kv: -kv[1]))

    levels = {}
    for lvl in ("temperature_level", "occupancy_level"):
        src = "temperature_c" if lvl == "temperature_level" else "occupancy_pct"
        g = df.groupby(lvl)[src].agg(["min", "max"])
        levels[lvl] = {k: [float(v["min"]), float(v["max"])] for k, v in g.iterrows()}

    return {
        "signature": dataset_signature(),
        "pipeline": pipe,
        "classes": classes,
        "metrics": {
            "accuracy": float(accuracy_score(y_te, pred)), "precision": float(p), "recall": float(r), "f1": float(f),
            "train_accuracy": float(accuracy_score(y_tr, pipe.predict(X_tr))),
            "train_size": int(len(X_tr)), "test_size": int(len(X_te)),
            "tree_depth": int(tree.get_depth()), "tree_leaves": int(tree.get_n_leaves()),
            "per_class": [{"class": c, "precision": float(pc[i]), "recall": float(rc[i]), "f1": float(fc[i]),
                           "support": int(sc[i])} for i, c in enumerate(classes)],
            "confusion_matrix": confusion_matrix(y_te, pred, labels=classes).tolist(),
            "importance": {"labels": list(importance), "values": [round(v, 4) for v in importance.values()]},
        },
        "tree": _tree_json(tree, names, list(tree.classes_)),
        "options": {
            "building_type": sorted(df["building_type"].unique().tolist()),
            "temperature_level": sorted(df["temperature_level"].unique().tolist()),
            "occupancy_level": sorted(df["occupancy_level"].unique().tolist()),
            "levels": levels,
            "ranges": {c: [float(df[c].min()), float(df[c].max()), round(float(df[c].mean()), 1)] for c in NUM_CLS},
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
            except Exception:  # corrupt / incompatible pickle -> retrain
                pass
        _state = _train(get_clean_df())
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(_state, MODEL_PATH, compress=3)
        return _state


def metrics():
    s = get_state()
    return {"model": "J48-style Decision Tree (entropy criterion, pre-pruned)", "classes": s["classes"],
            "features": NUM_CLS + CAT_CLS, **s["metrics"], "tree": s["tree"], "options": s["options"]}


def predict(payload):
    s = get_state()
    opt = s["options"]
    row = {}
    for col in NUM_CLS:
        try:
            val = float(payload.get(col))
        except (TypeError, ValueError):
            raise ValueError(f"'{col}' must be a number.")
        if not np.isfinite(val):
            raise ValueError(f"'{col}' must be a finite number.")
        row[col] = val
    if not 0 <= row["hour"] <= 23:
        raise ValueError("Hour must be between 0 and 23.")
    for col in ("humidity_pct", "occupancy_pct", "hvac_usage_pct", "lighting_usage_pct"):
        if not 0 <= row[col] <= 100:
            raise ValueError(f"'{col}' must be between 0 and 100.")
    for col in CAT_CLS:
        if payload.get(col) not in opt[col]:
            raise ValueError(f"'{col}' must be one of: {', '.join(opt[col])}.")
        row[col] = payload[col]
    X = pd.DataFrame([row])[NUM_CLS + CAT_CLS]
    pipe = s["pipeline"]
    proba = pipe.predict_proba(X)[0]
    probs = {c: float(p) for c, p in zip(pipe.classes_, proba)}
    label = pipe.predict(X)[0]
    return {"prediction": label, "confidence": probs[label],
            "probabilities": {c: probs.get(c, 0.0) for c in s["classes"]}}
