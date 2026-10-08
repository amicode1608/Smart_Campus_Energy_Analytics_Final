"""SQL-based aggregations for the Dashboard and Data Analysis pages."""
import sqlite3

from .preprocessing import DB_PATH, TABLE

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
CATEGORY_ORDER = ["Low", "Medium", "High"]
_FILTER_COLS = {"building": "building_name", "building_type": "building_type",
                "month": "month", "category": "energy_category"}


def _q(sql, params=()):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def _where(args):
    clauses, params = [], []
    for key, col in _FILTER_COLS.items():
        val = args.get(key)
        if val in (None, "", "all"):
            continue
        clauses.append(f"{col} = ?")
        params.append(int(val) if key == "month" else val)
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", params


def _month_label(m):
    return MONTHS[int(m) - 1]


def _series(rows, key, val, label=lambda x: x, nd=2):
    return {"labels": [label(r[key]) for r in rows], "values": [round(r[val] or 0, nd) for r in rows]}


def filter_options():
    return {
        "buildings": [r["building_name"] for r in _q(f"SELECT DISTINCT building_name FROM {TABLE} ORDER BY 1")],
        "building_types": [r["building_type"] for r in _q(f"SELECT DISTINCT building_type FROM {TABLE} ORDER BY 1")],
        "months": [{"value": r["month"], "label": _month_label(r["month"])}
                   for r in _q(f"SELECT DISTINCT month FROM {TABLE} ORDER BY 1")],
        "categories": [c for c in CATEGORY_ORDER
                       if _q(f"SELECT 1 FROM {TABLE} WHERE energy_category=? LIMIT 1", (c,))],
    }


def dashboard(args):
    w, p = _where(args)
    e = "energy_consumption_kwh"
    k = _q(f"""SELECT COUNT(*) n, SUM({e}) total, AVG({e}) avg, SUM(estimated_cost_inr) cost,
               SUM(co2_kg) co2, AVG(occupancy_pct) occ FROM {TABLE} {w}""", p)[0]
    top = _q(f"SELECT building_name, SUM({e}) t FROM {TABLE} {w} GROUP BY building_name ORDER BY t DESC LIMIT 1", p)
    monthly = _q(f"SELECT month, SUM({e}) v FROM {TABLE} {w} GROUP BY month ORDER BY month", p)
    hourly = _q(f"SELECT hour, AVG({e}) v FROM {TABLE} {w} GROUP BY hour ORDER BY hour", p)
    bld = _q(f"SELECT building_name, SUM({e}) v FROM {TABLE} {w} GROUP BY building_name ORDER BY v DESC", p)
    cat = {r["energy_category"]: r["n"] for r in
           _q(f"SELECT energy_category, COUNT(*) n FROM {TABLE} {w} GROUP BY energy_category", p)}
    occ = _q(f"SELECT ROUND(occupancy_pct/10.0)*10 b, AVG({e}) v FROM {TABLE} {w} GROUP BY b ORDER BY b", p)
    tmp = _q(f"SELECT ROUND(temperature_c/2.0)*2 b, AVG({e}) v FROM {TABLE} {w} GROUP BY b ORDER BY b", p)
    return {
        "kpis": {
            "records": k["n"], "total_energy": k["total"] or 0, "avg_energy": k["avg"] or 0,
            "total_cost": k["cost"] or 0, "total_co2": k["co2"] or 0, "avg_occupancy": k["occ"] or 0,
            "top_building": top[0]["building_name"] if top else "-",
        },
        "monthly": _series(monthly, "month", "v", _month_label),
        "hourly": _series(hourly, "hour", "v", lambda h: f"{int(h):02d}:00"),
        "building": _series(bld, "building_name", "v"),
        "category": {"labels": [c for c in CATEGORY_ORDER if c in cat], "values": [cat[c] for c in CATEGORY_ORDER if c in cat]},
        "occupancy": _series(occ, "b", "v", lambda b: f"{int(b)}%"),
        "temperature": _series(tmp, "b", "v", lambda b: f"{int(b)}°C"),
    }


def analysis():
    e = "energy_consumption_kwh"
    t = TABLE
    s = _q(f"""SELECT COUNT(*) n, COUNT(DISTINCT building_name) nb, AVG(temperature_c) temp, AVG(occupancy_pct) occ,
               SUM(estimated_cost_inr) cost, SUM(co2_kg) co2 FROM {t}""")[0]
    bld = _q(f"SELECT building_name, SUM({e}) v, SUM(estimated_cost_inr) cost, SUM(co2_kg) co2 FROM {t} "
             f"GROUP BY building_name ORDER BY v DESC")
    peak = _q(f"SELECT hour, SUM({e}) v FROM {t} GROUP BY hour ORDER BY v DESC LIMIT 1")[0]
    monthly = _q(f"SELECT month, SUM({e}) v FROM {t} GROUP BY month ORDER BY month")
    hourly = _q(f"SELECT hour, AVG({e}) v FROM {t} GROUP BY hour ORDER BY hour")
    occ = _q(f"SELECT ROUND(occupancy_pct/10.0)*10 b, AVG({e}) v FROM {t} GROUP BY b ORDER BY b")
    tmp = _q(f"SELECT ROUND(temperature_c/2.0)*2 b, AVG({e}) v FROM {t} GROUP BY b ORDER BY b")
    hv = _q(f"SELECT ROUND(hvac_usage_pct/10.0)*10 b, AVG({e}) v FROM {t} GROUP BY b ORDER BY b")
    return {
        "stats": {
            "records": s["n"], "buildings": s["nb"], "peak_hour": f"{int(peak['hour']):02d}:00",
            "highest_building": bld[0]["building_name"], "highest_value": bld[0]["v"],
            "lowest_building": bld[-1]["building_name"], "lowest_value": bld[-1]["v"],
            "avg_temperature": s["temp"], "avg_occupancy": s["occ"], "total_cost": s["cost"], "total_co2": s["co2"],
        },
        "monthly": _series(monthly, "month", "v", _month_label),
        "hourly": _series(hourly, "hour", "v", lambda h: f"{int(h):02d}:00"),
        "building": _series(bld, "building_name", "v"),
        "cost": _series(bld, "building_name", "cost"),
        "co2": _series(bld, "building_name", "co2"),
        "occupancy": _series(occ, "b", "v", lambda b: f"{int(b)}%"),
        "temperature": _series(tmp, "b", "v", lambda b: f"{int(b)}°C"),
        "hvac": _series(hv, "b", "v", lambda b: f"{int(b)}%"),
    }
