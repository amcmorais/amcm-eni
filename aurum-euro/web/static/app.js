
const $ = s => document.querySelector(s);
async function j(u){ const r = await fetch(u); return r.json(); }
async function boot(){
  const h = await j('/api/v1/health');
  $('#health').innerHTML = [
    ['Gold rows', h.gold_rows],
    ['Source obs', h.source_observations],
    ['€Au obs', h.au_observations],
    ['Last run', h.last_run ? h.last_run.status : '—']
  ].map(([k,v]) => `<div class="card"><div class="mut">${k}</div><strong>${v}</strong></div>`).join('');
  const ds = await j('/api/v1/datasets');
  const sel = $('#ds');
  (ds.datasets||[]).forEach(d => {
    const o=document.createElement('option'); o.value=d.id; o.textContent=d.id; sel.appendChild(o);
  });
  if(!sel.value){ const o=document.createElement('option'); o.value='nama_10_gdp'; o.textContent='nama_10_gdp'; sel.appendChild(o); }
}
async function load(){
  const id = $('#ds').value || 'nama_10_gdp';
  $('#csv').href = `/api/v1/download/${id}.csv`;
  $('#json').href = `/api/v1/download/${id}.json`;
  const data = await j('/api/v1/au/'+id);
  const tb = $('#tb');
  if(!data.rows || !data.rows.length){ tb.innerHTML = '<tr><td colspan="7">No rows. Run <code>python3 -m aurum.cli rebuild</code>.</td></tr>'; return; }
  tb.innerHTML = data.rows.map(r => `<tr>
    <td>${r.period}</td><td>${r.source_value}</td><td>${r.source_unit}</td>
    <td>${r.gold_price}</td><td>${r.gold_alignment_method}</td>
    <td>${r.au_value}</td><td>${r.au_unit}</td></tr>`).join('');
}
$('#go').addEventListener('click', load);
boot();
