"""Smart Campus Energy Analytics Using Data Mining - Flask application."""
import logging
from functools import wraps

import numpy as np
from flask import Flask, jsonify, render_template, request
from flask.json.provider import DefaultJSONProvider

from ml import analytics, association_rules, classification, clustering, preprocessing, regression

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("campus-energy")


class NumpyJSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if np.isnan(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return DefaultJSONProvider.default(o)


app = Flask(__name__)
app.json = NumpyJSONProvider(app)

# CSV -> SQLite on first start (skipped automatically when the table is already populated)
DB_STATUS = preprocessing.init_db()
log.info("Database ready: %s", DB_STATUS)

PAGES = {
    "dashboard": ("Dashboard", "Campus-wide energy KPIs with live filters"),
    "analysis": ("Data Analysis", "Consumption patterns across buildings, time and conditions"),
    "preprocessing": ("Preprocessing", "Cleaning, encoding, scaling and feature selection"),
    "association": ("Association Rules", "Apriori rule mining on categorical attributes"),
    "classification": ("J48 Classification", "J48-style decision tree predicting energy category"),
    "regression": ("Regression", "Random Forest model predicting energy consumption (kWh)"),
    "clustering": ("K-Means Clustering", "Usage profiles discovered with K-Means"),
}


def api(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        try:
            return jsonify(fn(*a, **kw))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except Exception as exc:  # noqa: BLE001
            log.exception("API error in %s", fn.__name__)
            return jsonify(error=f"Server error: {exc}"), 500
    return wrapper


def page(key):
    title, sub = PAGES[key]
    return render_template(f"{key}.html", page=key, page_title=title, page_subtitle=sub)


# ------------------------------------------------------------------ pages
@app.route("/")
@app.route("/dashboard")
def dashboard():
    return page("dashboard")


@app.route("/analysis")
def analysis():
    return page("analysis")


@app.route("/preprocessing")
def preprocessing_page():
    return page("preprocessing")


@app.route("/association")
def association():
    return page("association")


@app.route("/classification")
def classification_page():
    return page("classification")


@app.route("/regression")
def regression_page():
    return page("regression")


@app.route("/clustering")
def clustering_page():
    return page("clustering")


# ------------------------------------------------------------------ APIs
@app.route("/api/filters")
@api
def api_filters():
    return analytics.filter_options()


@app.route("/api/dashboard")
@api
def api_dashboard():
    return analytics.dashboard(request.args)


@app.route("/api/analysis")
@api
def api_analysis():
    return analytics.analysis()


@app.route("/api/preprocessing")
@api
def api_preprocessing():
    return preprocessing.preprocessing_report()


@app.route("/api/association")
@api
def api_association():
    return association_rules.mine_rules(request.args.get("min_support", 0.1), request.args.get("min_confidence", 0.6))


@app.route("/api/classification/metrics")
@api
def api_cls_metrics():
    return classification.metrics()


@app.route("/api/classification/predict", methods=["POST"])
@api
def api_cls_predict():
    return classification.predict(request.get_json(silent=True) or {})


@app.route("/api/regression/metrics")
@api
def api_reg_metrics():
    return regression.metrics()


@app.route("/api/regression/predict", methods=["POST"])
@api
def api_reg_predict():
    return regression.predict(request.get_json(silent=True) or {})


@app.route("/api/clustering")
@api
def api_clustering():
    return clustering.run(request.args.get("k", 3))


def warm_up():
    """Train (or load cached) models once at startup so the first page view is fast."""
    classification.get_state()
    regression.get_state()
    log.info("Models ready")


if __name__ == "__main__":
    warm_up()
    app.run(host="127.0.0.1", port=5000, debug=False)
