const NUM_FIELDS = ['temperature_c', 'humidity_pct', 'occupancy_pct', 'hvac_usage_pct', 'lighting_usage_pct', 'hour'];
let OPTIONS = null;

function treeHTML(n, branch) {
  const tag = branch ? `<span class="branch">${esc(branch)}</span>` : '';
  const info = `<span class="muted"> n=${fmt(n.samples)}, entropy ${n.entropy}</span>`;
  if (!n.left) {
    const note = n.truncated ? ' (further splits not shown)' : '';
    return `<li>${tag}<span class="tnode leaf ${n.label.toLowerCase()}">→ <b>${esc(n.label)}</b>${info}${note}</span></li>`;
  }
  return `<li>${tag}<span class="tnode"><b>${esc(n.split)}</b>${info}</span><ul>` +
    treeHTML(n.left, n.left_label) + treeHTML(n.right, n.right_label) + '</ul></li>';
}

function levelFor(levels, value) {
  let best = null, bestDist = Infinity;
  Object.entries(levels).forEach(([name, [lo, hi]]) => {
    const dist = value < lo ? lo - value : value > hi ? value - hi : 0;
    if (dist < bestDist) { best = name; bestDist = dist; }
  });
  return best;
}

function syncLevels() {
  const t = parseFloat($('temperature_c').value), o = parseFloat($('occupancy_pct').value);
  if (!isNaN(t)) $('temperature_level').value = levelFor(OPTIONS.levels.temperature_level, t);
  if (!isNaN(o)) $('occupancy_level').value = levelFor(OPTIONS.levels.occupancy_level, o);
}

(guard(async () => {
  const m = await api('/api/classification/metrics');
  OPTIONS = m.options;
  $('m-acc').textContent = pct(m.accuracy);
  $('m-prec').textContent = pct(m.precision);
  $('m-rec').textContent = pct(m.recall);
  $('m-f1').textContent = pct(m.f1);
  $('m-info').textContent = `Train/test split 80/20 (${fmt(m.train_size)} / ${fmt(m.test_size)} records). Tree depth ${m.tree_depth}, ${m.tree_leaves} leaves. ` +
    `Training accuracy ${pct(m.train_accuracy)}. All metrics are computed on the held-out test set.`;

  // confusion matrix with simple intensity shading
  const cm = m.confusion_matrix, max = Math.max(...cm.flat());
  let html = '<thead><tr><th>Actual \\ Predicted</th>' + m.classes.map((c) => `<th>${esc(c)}</th>`).join('') + '</tr></thead><tbody>';
  cm.forEach((row, i) => {
    html += `<tr><th>${esc(m.classes[i])}</th>` + row.map((v, j) => {
      const a = (v / max * 0.55).toFixed(2);
      const bg = i === j ? `rgba(37,99,235,${a})` : `rgba(220,38,38,${(v / max * 0.35).toFixed(2)})`;
      return `<td class="cell" style="background:${bg}">${fmt(v)}</td>`;
    }).join('') + '</tr>';
  });
  $('cm').innerHTML = html + '</tbody>';
  renderTable('per-class', ['Class', 'Precision', 'Recall', 'F1', 'Support'],
    m.per_class.map((c) => [badge(c.class), pct(c.precision), pct(c.recall), pct(c.f1), fmt(c.support)]), [1, 2, 3, 4]);

  barChart('imp-chart', { labels: m.importance.labels, values: m.importance.values }, 'Importance', C.blue, { horizontal: true, yTitle: 'Importance' });
  $('tree').innerHTML = treeHTML(m.tree, '');

  // prediction form
  fillSelect('building_type', OPTIONS.building_type.map((v) => [v, v]));
  fillSelect('temperature_level', OPTIONS.temperature_level.map((v) => [v, v]));
  fillSelect('occupancy_level', OPTIONS.occupancy_level.map((v) => [v, v]));
  NUM_FIELDS.forEach((f) => {
    const [lo, hi, mean] = OPTIONS.ranges[f];
    const el = $(f);
    el.min = Math.floor(lo); el.max = Math.ceil(hi);
    el.value = f === 'hour' ? Math.round(mean) : mean;
  });
  syncLevels();
  $('temperature_c').addEventListener('input', syncLevels);
  $('occupancy_pct').addEventListener('input', syncLevels);
}))();

$('predict-form').addEventListener('submit', guard(async (ev) => {
  ev.preventDefault();
  const body = { building_type: $('building_type').value, temperature_level: $('temperature_level').value, occupancy_level: $('occupancy_level').value };
  NUM_FIELDS.forEach((f) => { body[f] = $(f).value; });
  const r = await postJSON('/api/classification/predict', body);
  const probs = Object.entries(r.probabilities).map(([c, p]) =>
    `<div class="prob"><span class="name">${esc(c)}</span><div class="bar"><span style="width:${(p * 100).toFixed(1)}%"></span></div><span class="pct">${(p * 100).toFixed(1)}%</span></div>`).join('');
  const box = $('result');
  box.hidden = false;
  box.innerHTML = `<div class="muted small">Predicted Category</div><div class="big">${badge(r.prediction)}</div>
    <div class="muted small" style="margin:10px 0 4px">Class probabilities</div>${probs}`;
}));
