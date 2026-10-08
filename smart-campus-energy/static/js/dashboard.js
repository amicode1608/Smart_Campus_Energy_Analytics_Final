const FILTERS = { building: 'f-building', building_type: 'f-type', month: 'f-month', category: 'f-category' };

const load = guard(async () => {
  const qs = new URLSearchParams();
  Object.entries(FILTERS).forEach(([key, id]) => { if ($(id).value) qs.set(key, $(id).value); });
  const d = await api('/api/dashboard?' + qs.toString());
  const k = d.kpis;
  $('k-total').innerHTML = `${fmt(k.total_energy)} <span class="unit">kWh</span>`;
  $('k-avg').innerHTML = `${fmt(k.avg_energy, 2)} <span class="unit">kWh</span>`;
  $('k-cost').textContent = '₹ ' + fmt(k.total_cost);
  $('k-co2').innerHTML = `${fmt(k.total_co2)} <span class="unit">kg</span>`;
  $('k-occ').textContent = fmt(k.avg_occupancy, 1) + '%';
  $('k-top').textContent = k.top_building;
  $('record-count').textContent = `${fmt(k.records)} records match the selected filters.`;

  barChart('c-monthly', d.monthly, 'Energy (kWh)', C.blue, { yTitle: 'kWh' });
  lineChart('c-hourly', d.hourly, 'Avg kWh', C.green, { xTitle: 'Hour of day', yTitle: 'kWh' });
  barChart('c-building', d.building, 'Energy (kWh)', C.purple, { horizontal: true, yTitle: 'kWh' });
  chart('c-category', 'doughnut', {
    labels: d.category.labels,
    datasets: [{ data: d.category.values, backgroundColor: d.category.labels.map((l) => CAT_COLORS[l] || C.gray) }],
  }, { plugins: { legend: { position: 'bottom' } }, cutout: '55%' });
  lineChart('c-occ', d.occupancy, 'Avg kWh', C.orange, { xTitle: 'Occupancy', yTitle: 'kWh' });
  lineChart('c-temp', d.temperature, 'Avg kWh', C.red, { xTitle: 'Temperature', yTitle: 'kWh' });
});

(guard(async () => {
  const o = await api('/api/filters');
  fillSelect('f-building', o.buildings.map((b) => [b, b]), 'All buildings');
  fillSelect('f-type', o.building_types.map((b) => [b, b]), 'All types');
  fillSelect('f-month', o.months.map((m) => [m.value, m.label]), 'All months');
  fillSelect('f-category', o.categories.map((c) => [c, c]), 'All categories');
  Object.values(FILTERS).forEach((id) => $(id).addEventListener('change', load));
  $('reset').addEventListener('click', () => { Object.values(FILTERS).forEach((id) => { $(id).value = ''; }); load(); });
  await load();
}))();
