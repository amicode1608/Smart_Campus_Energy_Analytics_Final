(guard(async () => {
  const d = await api('/api/analysis');
  const s = d.stats;
  $('s-records').textContent = fmt(s.records);
  $('s-buildings').textContent = fmt(s.buildings);
  $('s-peak').textContent = s.peak_hour;
  $('s-high').innerHTML = `${esc(s.highest_building)}<div class="unit">${fmt(s.highest_value)} kWh</div>`;
  $('s-low').innerHTML = `${esc(s.lowest_building)}<div class="unit">${fmt(s.lowest_value)} kWh</div>`;
  $('s-temp').textContent = fmt(s.avg_temperature, 1) + ' °C';
  $('s-occ').textContent = fmt(s.avg_occupancy, 1) + '%';
  $('s-cost').textContent = '₹ ' + fmt(s.total_cost);
  $('s-co2').innerHTML = `${fmt(s.total_co2)} <span class="unit">kg</span>`;

  barChart('a-monthly', d.monthly, 'Energy (kWh)', C.blue, { yTitle: 'kWh' });
  lineChart('a-hourly', d.hourly, 'Avg kWh', C.green, { xTitle: 'Hour of day', yTitle: 'kWh' });
  barChart('a-building', d.building, 'Energy (kWh)', C.purple, { yTitle: 'kWh' });
  barChart('a-cost', d.cost, 'Cost (₹)', C.orange, { yTitle: '₹' });
  barChart('a-co2', d.co2, 'CO₂ (kg)', C.teal, { yTitle: 'kg' });
  lineChart('a-occ', d.occupancy, 'Avg kWh', C.orange, { xTitle: 'Occupancy', yTitle: 'kWh' });
  lineChart('a-temp', d.temperature, 'Avg kWh', C.red, { xTitle: 'Temperature', yTitle: 'kWh' });
  lineChart('a-hvac', d.hvac, 'Avg kWh', C.blue, { xTitle: 'HVAC usage', yTitle: 'kWh' });
}))();
