
const $ = s => document.querySelector(s);
async function j(u){
  try {
    const r = await fetch(u);
    if (r.ok) return r.json();
  } catch (e) {}
  const r2 = await fetch('snapshot.json');
  if (!r2.ok) throw new Error('no snapshot');
  const snap = await r2.json();
  if (u.includes('/health') || u.includes('/status')) return {
    gold_rows: snap.status.gold_rows,
    source_observations: snap.status.source_observations,
    au_observations: snap.status.au_observations,
    last_run: snap.status.last_run
  };
  if (u.includes('/datasets')) return {datasets: snap.datasets};
  if (u.includes('/au/')) {
    const id = u.split('/au/')[1].split('?')[0];
    const rows = (snap.observations[id] || []);
    return {dataset:id, n: rows.length, rows};
  }
  return snap;
}
async function boot(){
  const h = await j('/api/v1/health');
  $('#health').innerHTML = [
    ['Gold rows', h.gold_rows],
    ['Source obs', h.source_observations],
    ['€Au obs', h.au_observations],
    ['Last run', (h.last_run && h.last_run.status) ? h.last_run.status : (h.last_run || '—')]
  ].map(([k,v]) => `<div class="card"><div class="mut">${k}</div><strong>${v}</strong></div>`).join('');
  const ds = await j('/api/v1/datasets');
  const sel = $('#ds');
  (ds.datasets||[]).forEach(d => {
    const o=document.createElement('option'); o.value=d.id; o.textContent=d.id; sel.appendChild(o);
  });
  if(!sel.value){ const o=document.createElement('option'); o.value='nama_10_gdp'; o.textContent='nama_10_gdp'; sel.appendChild(o); }
  load();
}
async function load(){
  const id = ($('#ds') && $('#ds').value) || 'nama_10_gdp';
  const csv = document.getElementById('csv');
  const js = document.getElementById('json');
  if (csv) csv.href = `/aurum-euro/api/v1/download/${id}.csv`;
  if (js) js.href = `/aurum-euro/api/v1/download/${id}.json`;
  const data = await j('/api/v1/au/'+id);
  const tb = $('#tb');
  if(!data.rows || !data.rows.length){ tb.innerHTML = '<tr><td colspan="7">No rows.</td></tr>'; return; }
  tb.innerHTML = data.rows.map(r => `<tr>
    <td>${r.period}</td><td>${r.source_value}</td><td>${r.source_unit}</td>
    <td>${r.gold_price}</td><td>${r.gold_alignment_method}</td>
    <td>${Number(r.au_value).toFixed(4)}</td><td>${r.au_unit}</td></tr>`).join('');
}
document.getElementById('go').addEventListener('click', load);
boot();
