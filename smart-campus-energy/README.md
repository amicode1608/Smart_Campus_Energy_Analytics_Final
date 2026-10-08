# Smart Campus Energy Analytics Using Data Mining

A DWM (Data Warehousing & Data Mining) college mini-project. A Flask web application that stores campus energy
records in SQLite and applies five data mining concepts with interactive charts and live predictions.

> **The dataset is synthetic and created for academic purposes. It is not real-world data.**

## Objectives
- Store and query campus energy data using a CSV → SQLite pipeline.
- Explore consumption patterns by building, hour, month, occupancy and temperature.
- Apply core DWM techniques: preprocessing, association rules, classification, regression and clustering.
- Provide prediction forms for energy category and energy consumption.

## DWM Concepts Used
1. Data Preprocessing
2. Association Rule Mining (Apriori)
3. J48-style Decision Tree Classification
4. Regression (Random Forest)
5. K-Means Clustering

## Technology Stack
| Layer | Tools |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript, Chart.js |
| Backend | Python, Flask |
| Data | Pandas, NumPy, SQLite |
| Machine learning | scikit-learn, mlxtend, joblib |

## Dataset
`data/smart_campus_energy_analytics_8000.csv` holds 8,000 hourly records for several campus buildings (synthetic data).

Columns: `building_id, building_name, building_type, floor_area_sqft, floor_count, timestamp, hour, day_of_week,
month, is_weekend, temperature_c, humidity_pct, occupancy_pct, occupancy_level, hvac_usage_pct, lighting_usage_pct,
temperature_level, energy_consumption_kwh, energy_category, estimated_cost_inr, co2_kg, anomaly_flag`

On first start the app imports the CSV into `database/campus_energy.db` (table `campus_energy`). The import is skipped
on later starts when the table already holds the same number of rows, so restarting never creates duplicates.
The CSV is never modified. Dashboard and analysis numbers are computed with SQL queries on this table.

## Project Structure
```
smart-campus-energy/
├── app.py                  Flask routes + JSON APIs
├── requirements.txt
├── data/                   source CSV
├── database/               campus_energy.db (created automatically)
├── models/                 classification_model.pkl, regression_model.pkl (created automatically)
├── ml/
│   ├── preprocessing.py    CSV→SQLite import, cleaning, preprocessing report
│   ├── analytics.py        SQL aggregations for Dashboard / Data Analysis
│   ├── association_rules.py
│   ├── classification.py
│   ├── regression.py
│   └── clustering.py
├── templates/              one HTML page per section (base.html = layout + sidebar)
└── static/
    ├── css/style.css
    └── js/                 common.js + one script per page
```

## Installation
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
```

## How to Run
```bash
python app.py
```
Open http://127.0.0.1:5000. Models are trained once at startup and cached in `models/` (they are retrained
automatically if the CSV changes). Chart.js is loaded from a CDN; for offline use, save `chart.umd.min.js`
(Chart.js 4.4.1) into `static/js/vendor/` and the app will use it automatically.

## DWM Concepts Explained
- **Preprocessing** – removes duplicates, fills missing values (median / mode), converts `timestamp` to datetime,
  one-hot/ordinal encodes categories, z-score scales numeric columns and selects features. Leakage columns
  (`energy_consumption_kwh` for classification, `estimated_cost_inr`, `co2_kg`, `energy_category`) are excluded.
  Everything is done in memory; the CSV and DB are untouched.
- **Association Rules** – Apriori over `building_type, occupancy_level, temperature_level, energy_category` and
  weekday/weekend. Support, confidence and lift are computed for the user-supplied thresholds. Uses `mlxtend`
  (a built-in Apriori is used only if mlxtend is missing).
- **J48-style Decision Tree** – `DecisionTreeClassifier(criterion="entropy")` (information gain, like C4.5/J48,
  with pre-pruning) predicting `energy_category` (Low/Medium/High) from weather, occupancy, HVAC, lighting, hour and
  building features. 80/20 stratified split; accuracy, precision, recall, F1 and the confusion matrix come from the test set.
- **Regression** – `RandomForestRegressor` predicting `energy_consumption_kwh`; MAE, RMSE and R² from the test set.
  The prediction form also returns cost (`kWh × 8.5` INR) and CO₂ (`kWh × 0.71` kg).
- **K-Means** – standardised temperature, occupancy, HVAC, lighting and energy; K = 2–5; reports cluster sizes,
  averages, silhouette score and a PCA scatter plot.

## Pages
| Route | Description |
|---|---|
| `/`, `/dashboard` | KPIs, 6 charts, filters (building, type, month, category) |
| `/analysis` | Extended statistics and 8 charts |
| `/preprocessing` | Before → after summary and preprocessing details |
| `/association` | Apriori rule generator (support/confidence inputs) |
| `/classification` | J48-style tree metrics, confusion matrix, tree view, category prediction |
| `/regression` | Regression metrics, charts, energy/cost/CO₂ prediction |
| `/clustering` | K-Means with K = 2–5 |

## Future Scope
Time-series forecasting, real IoT/smart-meter data, anomaly detection, user login, report export and deployment on a cloud server.
