function statBlock(s) {
  return [['Rows', s.rows], ['Columns', s.columns], ['Missing values', s.missing_total], ['Duplicate records', s.duplicates]]
    .map(([k, v]) => `<div class="stat-row"><span>${k}</span><strong>${fmt(v)}</strong></div>`).join('');
}

(guard(async () => {
  const d = await api('/api/preprocessing');
  $('before').innerHTML = statBlock(d.before);
  $('after').innerHTML = statBlock(d.after);

  renderTable('t-steps', ['Step', 'Result'], d.steps.map((s) => [esc(s.step), esc(s.result)]));
  renderTable('t-missing', ['Column', 'Missing', '%'],
    d.missing_by_col.length ? d.missing_by_col.map((m) => [esc(m.column), fmt(m.missing), m.pct + '%']) : [['No missing values found', '0', '0%']], [1, 2]);
  $('ts-info').innerHTML = `Type: <code>${esc(d.timestamp.before)}</code> → <code>${esc(d.timestamp.after)}</code><br>Range: ${esc(d.timestamp.min)} to ${esc(d.timestamp.max)}`;

  renderTable('t-encoding', ['Column', 'Method', 'Categories', 'New cols'],
    d.encoding.map((e) => [esc(e.column), esc(e.method), esc(e.categories.join(', ')), e.new_columns]), [3]);
  renderTable('t-scaling', ['Column', 'Mean (before)', 'Std (before)', 'Mean (after)', 'Std (after)'],
    d.scaling.map((s) => [esc(s.column), s.mean_before, s.std_before, s.mean_after, s.std_after]), [1, 2, 3, 4]);
  renderTable('t-selection', ['Feature', 'Corr. with energy', 'F-score vs category', 'Used in'],
    d.selection.map((s) => [esc(s.feature), s.corr_with_energy ?? '-', s.f_score_vs_category ?? '-', esc(s.used_in)]), [1, 2]);
  renderTable('t-excluded', ['Column', 'Reason'], d.excluded.map((e) => [esc(e.column), esc(e.reason)]));

  const cols = (rows) => Object.keys(rows[0] || {});
  renderTable('t-preview', cols(d.preview), d.preview.map((r) => Object.values(r).map(esc)));
  renderTable('t-scaled', cols(d.scaled_preview), d.scaled_preview.map((r) => Object.values(r).map(esc)));
}))();
