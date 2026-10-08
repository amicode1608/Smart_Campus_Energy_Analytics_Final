"""Apriori association rule mining (mlxtend, with a built-in Apriori fallback)."""
import inspect
from itertools import combinations

import pandas as pd

from .preprocessing import get_clean_df

ITEM_COLS = ["building_type", "occupancy_level", "temperature_level", "energy_category", "is_weekend"]

try:  # preferred engine
    from mlxtend.frequent_patterns import apriori as _mlx_apriori
    from mlxtend.frequent_patterns import association_rules as _mlx_rules
    ENGINE = "mlxtend"
except ImportError:  # pragma: no cover - only when mlxtend is not installed
    ENGINE = "built-in Apriori (mlxtend not installed)"


def transactions():
    """One-hot transaction table: each row = one record, each column = 'attribute=value'."""
    df = get_clean_df()[ITEM_COLS].copy()
    df["is_weekend"] = df["is_weekend"].astype(int).map({0: "Weekday", 1: "Weekend"})
    df = df.rename(columns={"is_weekend": "day_type"})
    return pd.get_dummies(df.astype(str), prefix_sep="=", dtype=bool)


# ------------------------------------------------------------ built-in Apriori
def _apriori_builtin(onehot, min_support, max_len):
    arr = onehot.to_numpy(dtype=bool)
    cols = list(onehot.columns)
    sup = arr.mean(axis=0)
    freq = {frozenset([cols[i]]): float(sup[i]) for i in range(len(cols)) if sup[i] >= min_support}
    level = list(freq)
    k = 2
    while level and k <= max_len:
        prev = set(level)
        cands = set()
        for a, b in combinations(level, 2):
            u = a | b
            if len(u) == k and all(frozenset(s) in prev for s in combinations(u, k - 1)):
                cands.add(u)
        level = []
        for c in cands:
            idx = [cols.index(x) for x in c]
            s = float(arr[:, idx].all(axis=1).mean())
            if s >= min_support:
                freq[c] = s
                level.append(c)
        k += 1
    return freq


def _rules_builtin(freq, min_conf):
    rows = []
    for items, s in freq.items():
        if len(items) < 2:
            continue
        for r in range(1, len(items)):
            for ant in combinations(items, r):
                ant = frozenset(ant)
                cons = items - ant
                conf = s / freq[ant]
                if conf >= min_conf:
                    rows.append({"antecedents": ant, "consequents": cons, "support": s,
                                 "confidence": conf, "lift": conf / freq[cons]})
    return pd.DataFrame(rows, columns=["antecedents", "consequents", "support", "confidence", "lift"])


def _mine(onehot, min_support, min_conf, max_len):
    if ENGINE == "mlxtend":
        freq = _mlx_apriori(onehot, min_support=min_support, use_colnames=True, max_len=max_len)
        if freq.empty:
            return 0, pd.DataFrame()
        kwargs = {"metric": "confidence", "min_threshold": min_conf}
        if "num_itemsets" in inspect.signature(_mlx_rules).parameters:
            kwargs["num_itemsets"] = len(onehot)
        return len(freq), _mlx_rules(freq, **kwargs)
    freq = _apriori_builtin(onehot, min_support, max_len)
    return len(freq), _rules_builtin(freq, min_conf)


def mine_rules(min_support, min_confidence, limit=200):
    min_support, min_confidence = float(min_support), float(min_confidence)
    if not 0 < min_support <= 1:
        raise ValueError("Minimum support must be between 0 and 1 (e.g. 0.10).")
    if not 0 < min_confidence <= 1:
        raise ValueError("Minimum confidence must be between 0 and 1 (e.g. 0.60).")
    onehot = transactions()
    n_itemsets, rules = _mine(onehot, min_support, min_confidence, max_len=len(ITEM_COLS))
    out = {"engine": ENGINE, "transactions": int(len(onehot)), "items": int(onehot.shape[1]),
           "frequent_itemsets": int(n_itemsets), "total_rules": 0, "rules": [], "chart": {"labels": [], "lift": [], "confidence": []}}
    if rules.empty:
        return out
    rules = rules.sort_values(["lift", "confidence", "support"], ascending=False).reset_index(drop=True)
    fmt = lambda s: ", ".join(sorted(s))  # noqa: E731
    rows = [{"antecedent": fmt(r.antecedents), "consequent": fmt(r.consequents),
             "support": round(float(r.support), 4), "confidence": round(float(r.confidence), 4),
             "lift": round(float(r.lift), 3)} for r in rules.head(limit).itertuples()]
    top = rows[:10]
    out.update(total_rules=int(len(rules)), rules=rows, chart={
        "labels": [f"{r['antecedent']} → {r['consequent']}" for r in top],
        "lift": [r["lift"] for r in top], "confidence": [r["confidence"] for r in top]})
    return out
