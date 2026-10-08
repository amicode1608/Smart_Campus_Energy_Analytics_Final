const NUM_FIELDS = ['floor_area_sqft', 'temperature_c', 'humidity_pct', 'occupancy_pct', 'hvac_usage_pct', 'lighting_usage_pct', 'hour'];
let OPTIONS = null;

(guard(async () => {
  const m = await api('/api/regression/metrics');
  OPTIONS = m.options;
  $('m-mae').innerHTML = `${m.mae.toFixed(2)} <span class="unit">kWh</span>`;
  $('m-rmse').innerHTML = `${m.rmse.toFixed(2)} <span class="unit">kWh</span>`;
  $('m-r2').textContent = m.r2.toFixed(3);
  $('m-n').textContent = fmt(m.test_size);
  $('m-info').textContent = `${m.model}. Train/test split 80/20 (${fmt(m.train_size)} / ${fmt(m.test_size)} records); average energy per record is ${m.mean_energy.toFixed(2)} kWh. Metrics come from the test set.`;

  const pts = m.scatter.actual.map((a, i) => ({ x: a, y: m.scatter.predicted[i] }));
  const lo = Math.min(...m.scatter.actual, ...m.scatter.predicted), hi = Math.max(...m.scatter.actual, ...m.scatter.predicted);
  chart('c-scatter', 'scatter', {
    datasets: [
      { label: 'Test records', data: pts, backgroundColor: C.blue + '99', pointRadius: 3 },
      { label: 'Perfect prediction', data: [{ x: lo, y: lo }, { x: hi, y: hi }], type: 'line', borderColor: C.red, borderDash: [6, 4], pointRadius: 0, fill: false },
    ],
  }, {
    scales: { x: { title: { display: true, text: 'Actual (kWh)' }, grid: { color: '#eef2f7' } }, y: { title: { display: true, text: 'Predicted (kWh)' }, grid: { color: '#eef2f7' } } },
    plugins: { legend: { position: 'bottom' } },
  });
  barChart('c-resid', { labels: m.residuals.labels, values: m.residuals.counts }, 'Records', C.purple, { xTitle: 'Residual (kWh)', yTitle: 'Records' });
  chart('c-trend', 'line', {
    labels: m.trend.labels,
    datasets: [
      { label: 'Actual', data: m.trend.actual, borderColor: C.blue, tension: 0.3, pointRadius: 3 },
      { label: 'Predicted', data: m.trend.predicted, borderColor: C.orange, borderDash: [6, 4], tension: 0.3, pointRadius: 3 },
    ],
  }, { scales: scales('Hour of day', 'kWh'), plugins: { legend: { position: 'bottom' } } });
  barChart('c-imp', { labels: m.importance.labels, values: m.importance.values }, 'Importance', C.green, { horizontal: true, yTitle: 'Importance' });

  fillSelect('building_type', OPTIONS.building_type.map((v) => [v, v]));
  NUM_FIELDS.forEach((f) => {
    const [lo2, hi2, mean] = OPTIONS.ranges[f];
    const el = $(f);
    el.value = f === 'hour' ? Math.round(mean) : f === 'floor_area_sqft' ? Math.round(mean) : mean;
    if (f !== 'floor_area_sqft') { el.min = Math.floor(lo2); el.max = Math.ceil(hi2); }
  });
  const setArea = () => { $('floor_area_sqft').value = OPTIONS.floor_area[$('building_type').value]; };
  $('building_type').addEventListener('change', setArea);
  setArea();
}))();

$('predict-form').addEventListener('submit', guard(async (ev) => {
  ev.preventDefault();
  const body = { building_type: $('building_type').value };
  NUM_FIELDS.forEach((f) => { body[f] = $(f).value; });
  const r = await postJSON('/api/regression/predict', body);
  const box = $('result');
  box.hidden = false;
  box.innerHTML = `<div class="result-grid">
    <div><div class="muted small">Predicted Energy Consumption</div><div class="big">${fmt(r.energy_kwh, 2)} kWh</div></div>
    <div><div class="muted small">Estimated Cost (× ₹8.5 / kWh)</div><div class="big">₹ ${fmt(r.cost_inr, 2)}</div></div>
    <div><div class="muted small">Estimated CO₂ (× 0.71 kg / kWh)</div><div class="big">${fmt(r.co2_kg, 2)} kg</div></div></div>`;
}));
