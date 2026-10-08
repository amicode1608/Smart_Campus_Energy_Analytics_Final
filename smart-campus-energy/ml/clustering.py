"""K-Means clustering of campus usage profiles."""
import threading

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .preprocessing import NUM_CLU, get_clean_df

ALLOWED_K = (2, 3, 4, 5)
FRIENDLY = {"temperature_c": "temperature", "occupancy_pct": "occupancy", "hvac_usage_pct": "HVAC usage",
            "lighting_usage_pct": "lighting usage", "energy_consumption_kwh": "energy"}
_lock = threading.RLock()
_cache = {}


def _describe(z):
    parts = []
    for col, v in zip(NUM_CLU, z):
        if v >= 0.5:
            parts.append(f"high {FRIENDLY[col]}")
        elif v <= -0.5:
            parts.append(f"low {FRIENDLY[col]}")
    return ", ".join(parts).capitalize() if parts else "Close to the campus average on all features"


def run(k):
    try:
        k = int(k)
    except (TypeError, ValueError):
        raise ValueError("K must be 2, 3, 4 or 5.")
    if k not in ALLOWED_K:
        raise ValueError("K must be 2, 3, 4 or 5.")
    with _lock:
        if k in _cache:
            return _cache[k]
        df = get_clean_df()
        X = df[NUM_CLU]
        Xs = StandardScaler().fit_transform(X)
        km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(Xs)

        # renumber clusters by ascending average energy so "Cluster 1" is always the lowest-energy group
        energy_means = [X["energy_consumption_kwh"][km.labels_ == c].mean() for c in range(k)]
        remap = {old: new for new, old in enumerate(np.argsort(energy_means))}
        labels = np.array([remap[l] for l in km.labels_])
        centers_z = np.zeros((k, len(NUM_CLU)))
        for old, new in remap.items():
            centers_z[new] = km.cluster_centers_[old]

        sil = float(silhouette_score(Xs, labels, sample_size=min(3000, len(Xs)), random_state=42))
        pca = PCA(n_components=2, random_state=42).fit(Xs)
        pts = pca.transform(Xs)
        rng = np.random.default_rng(42)
        idx = rng.choice(len(Xs), size=min(900, len(Xs)), replace=False)

        clusters = []
        for c in range(k):
            m = labels == c
            sub = X[m]
            ez = centers_z[c][NUM_CLU.index("energy_consumption_kwh")]
            tier = "High" if ez >= 0.5 else "Low" if ez <= -0.5 else "Medium"
            clusters.append({
                "id": c + 1, "name": f"Cluster {c + 1} ({tier} energy)", "size": int(m.sum()),
                "percent": round(float(m.mean() * 100), 1),
                "avg_energy": round(float(sub["energy_consumption_kwh"].mean()), 2),
                "avg_occupancy": round(float(sub["occupancy_pct"].mean()), 1),
                "avg_hvac": round(float(sub["hvac_usage_pct"].mean()), 1),
                "avg_lighting": round(float(sub["lighting_usage_pct"].mean()), 1),
                "avg_temperature": round(float(sub["temperature_c"].mean()), 1),
                "description": _describe(centers_z[c]),
            })
        scatter = [[{"x": round(float(pts[i, 0]), 3), "y": round(float(pts[i, 1]), 3)} for i in idx if labels[i] == c]
                   for c in range(k)]
        _cache[k] = {
            "k": k, "features": NUM_CLU, "silhouette": round(sil, 3), "inertia": round(float(km.inertia_), 1),
            "explained_variance": [round(float(v) * 100, 1) for v in pca.explained_variance_ratio_],
            "records": int(len(df)), "clusters": clusters, "scatter": scatter,
        }
        return _cache[k]
