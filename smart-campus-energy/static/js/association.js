const generate = guard(async () => {
  const btn = $('generate');
  btn.disabled = true;
  btn.textContent = 'Generating...';
  try {
    const qs = new URLSearchParams({ min_support: $('min-support').value, min_confidence: $('min-conf').value });
    const d = await api('/api/association?' + qs.toString());
    $('r-trans').textContent = fmt(d.transactions);
    $('r-sets').textContent = fmt(d.frequent_itemsets);
    $('r-rules').textContent = fmt(d.total_rules);
    $('r-engine').textContent = d.engine;

    renderTable('r-table', ['#', 'Antecedent (IF)', 'Consequent (THEN)', 'Support', 'Confidence', 'Lift'],
      d.rules.map((r, i) => [i + 1, esc(r.antecedent), esc(r.consequent), r.support.toFixed(3), r.confidence.toFixed(3), r.lift.toFixed(2)]), [3, 4, 5]);
    if (!d.rules.length) {
      $('r-table').querySelector('td').textContent = 'No rules found. Try lowering minimum support or confidence.';
    }

    chart('r-chart', 'bar', {
      labels: d.chart.labels,
      datasets: [
        { label: 'Lift', data: d.chart.lift, backgroundColor: C.blue, borderRadius: 3 },
        { label: 'Confidence', data: d.chart.confidence, backgroundColor: C.green, borderRadius: 3 },
      ],
    }, {
      indexAxis: 'y',
      scales: { x: { beginAtZero: true, grid: { color: '#eef2f7' } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } },
      plugins: { legend: { position: 'bottom' } },
    });
  } finally {
    btn.disabled = false;
    btn.textContent = 'Generate Rules';
  }
});

$('generate').addEventListener('click', generate);
generate();
