/* Shared helpers: fetch wrapper, formatting, Chart.js shortcuts */
const C = { blue: '#2563eb', green: '#16a34a', orange: '#f59e0b', purple: '#7c3aed', red: '#dc2626', gray: '#94a3b8', teal: '#0d9488' };
const PALETTE = [C.blue, C.green, C.orange, C.purple, C.red, C.teal];
const CAT_COLORS = { Low: C.green, Medium: C.orange, High: C.red };
const charts = {};

if (window.Chart) {
  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = '#475569';
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
} else {
  document.addEventListener('DOMContentLoaded', () =>
    showError('Chart.js could not be loaded (no internet?). Place chart.umd.min.js in static/js/vendor/ and reload.'));
}

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (n, d = 0) => Number(n ?? 0).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (x, d = 1) => (Number(x) * 100).toFixed(d) + '%';

function showError(msg) {
  const el = $('error');
  if (!el) return;
  el.textContent = msg;
  el.hidden = !msg;
}

async function api(url, options) {
  const res = await fetch(url, options);
  let data = null;
  try { data = await res.json(); } catch (e) { /* not JSON */ }
  if (!res.ok) throw new Error((data && data.error) || `Request failed (${res.status})`);
  showError('');
  return data;
}

function postJSON(url, body) {
  return api(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

function chart(id, type, data, options = {}) {
  if (!window.Chart || !$(id)) return null;
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), { type, data, options: { responsive: true, maintainAspectRatio: false, ...options } });
  return charts[id];
}

function scales(xTitle, yTitle, extra = {}) {
  return {
    x: { title: { display: !!xTitle, text: xTitle }, grid: { display: false }, ...(extra.x || {}) },
    y: { title: { display: !!yTitle, text: yTitle }, beginAtZero: true, grid: { color: '#eef2f7' }, ...(extra.y || {}) },
  };
}

function barChart(id, s, label, color, o = {}) {
  chart(id, 'bar', { labels: s.labels, datasets: [{ label, data: s.values, backgroundColor: color, borderRadius: 3 }] }, {
    indexAxis: o.horizontal ? 'y' : 'x',
    plugins: { legend: { display: false } },
    scales: o.horizontal
      ? { x: { beginAtZero: true, title: { display: !!o.yTitle, text: o.yTitle }, grid: { color: '#eef2f7' } }, y: { grid: { display: false } } }
      : scales(o.xTitle, o.yTitle),
  });
}

function lineChart(id, s, label, color, o = {}) {
  chart(id, 'line', {
    labels: s.labels,
    datasets: [{ label, data: s.values, borderColor: color, backgroundColor: color + '22', fill: true, tension: 0.3, pointRadius: 3 }],
  }, { plugins: { legend: { display: false } }, scales: scales(o.xTitle, o.yTitle) });
}

function renderTable(id, headers, rows, numericCols = []) {
  const head = headers.map((h, i) => `<th class="${numericCols.includes(i) ? 'num' : ''}">${esc(h)}</th>`).join('');
  const body = rows.map((r) => '<tr>' + r.map((c, i) => `<td class="${numericCols.includes(i) ? 'num' : ''}">${c}</td>`).join('') + '</tr>').join('');
  $(id).innerHTML = `<thead><tr>${head}</tr></thead><tbody>${body || `<tr><td colspan="${headers.length}" class="muted">No data</td></tr>`}</tbody>`;
}

function fillSelect(id, items, allLabel) {
  const sel = $(id);
  sel.innerHTML = (allLabel ? `<option value="">${esc(allLabel)}</option>` : '') +
    items.map(([v, t]) => `<option value="${esc(v)}">${esc(t)}</option>`).join('');
}

function badge(cls) { return `<span class="badge ${String(cls).toLowerCase()}">${esc(cls)}</span>`; }

function guard(fn) {
  return async (...a) => { try { await fn(...a); } catch (e) { showError(e.message); } };
}
