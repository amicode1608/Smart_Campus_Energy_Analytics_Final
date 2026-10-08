const loadK = guard(async (k) => {
  document.querySelectorAll('#k-buttons .btn').forEach((b) => b.classList.toggle('active', b.dataset.k === String(k)));
  const d = await api('/api/clustering?k=' + k);
  $('c-records').textContent = fmt(d.records);
  $('c-k').textContent = d.k;
  $('c-sil').textContent = d.silhouette.toFixed(3);
  $('c-inertia').textContent = fmt(d.inertia, 1);

  renderTable('c-table',
    ['Cluster', 'Size', '% of data', 'Avg energy (kWh)', 'Avg occupancy (%)', 'Avg HVAC (%)', 'Avg lighting (%)', 'Avg temp (°C)', 'Characteristics'],
    d.clusters.map((c, i) => [
      `<span style="color:${PALETTE[i]}">●</span> ${esc(c.name)}`, fmt(c.size), c.percent + '%', c.avg_energy, c.avg_occupancy,
      c.avg_hvac, c.avg_lighting, c.avg_temperature, esc(c.description)]), [1, 2, 3, 4, 5, 6, 7]);

  $('pca-note').textContent = `(PCA, ${d.explained_variance[0] + d.explained_variance[1]}% variance)`;
  chart('c-scatter', 'scatter', {
    datasets: d.clusters.map((c, i) => ({ label: `Cluster ${c.id}`, data: d.scatter[i], backgroundColor: PALETTE[i] + 'aa', pointRadius: 3 })),
  }, {
    scales: { x: { title: { display: true, text: 'PC1' }, grid: { color: '#eef2f7' } }, y: { title: { display: true, text: 'PC2' }, grid: { color: '#eef2f7' } } },
    plugins: { legend: { position: 'bottom' } },
  });
  const labels = d.clusters.map((c) => `Cluster ${c.id}`);
  chart('c-energy', 'bar', { labels, datasets: [{ data: d.clusters.map((c) => c.avg_energy), backgroundColor: PALETTE, borderRadius: 3 }] },
    { plugins: { legend: { display: false } }, scales: scales(null, 'kWh') });
  chart('c-occ', 'bar', { labels, datasets: [{ data: d.clusters.map((c) => c.avg_occupancy), backgroundColor: PALETTE, borderRadius: 3 }] },
    { plugins: { legend: { display: false } }, scales: scales(null, 'Occupancy %') });
});

document.querySelectorAll('#k-buttons .btn').forEach((b) => b.addEventListener('click', () => loadK(b.dataset.k)));
loadK(3);
