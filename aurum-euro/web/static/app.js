const $ = s => document.querySelector(s);
let SNAP = null;
async function loadSnap(){
  if (SNAP) return SNAP;
  const urls = ['/aurum-euro/snapshot.json','snapshot.json','/snapshot.json'];
  for (const u of urls){
    try { const r=await fetch(u); if(r.ok){ SNAP=await r.json(); return SNAP; } } catch(e){}
  }
  throw new Error('snapshot missing');
}
async function boot(){
  const snap = await loadSnap();
  const h = snap.status || {};
  $('#health').innerHTML = [
    ['Gold rows', h.gold_rows],
    ['Source obs', h.source_observations],
    ['€Au obs', h.au_observations],
    ['STOXX', h.stoxx || '—']
  ].map(([k,v]) => `<div class="card"><div class="mut">${k}</div><strong>${v}</strong></div>`).join('');
  const sel = $('#ds');
  sel.innerHTML = '';
  (snap.series||[]).forEach(id => {
    const o=document.createElement('option'); o.value=id; o.textContent=id; sel.appendChild(o);
  });
  load();
}
async function load(){
  const snap = await loadSnap();
  const id = $('#ds').value || (snap.series||[])[0];
  const rows = (snap.observations && snap.observations[id]) || [];
  const tb = $('#tb');
  if(!rows.length){ tb.innerHTML='<tr><td colspan="7">No rows.</td></tr>'; return; }
  tb.innerHTML = rows.map(r => `<tr>
    <td>${r.period}</td><td>${r.source_value}</td><td>${r.source_unit}</td>
    <td>${r.gold_price}</td><td>${r.gold_alignment_method}</td>
    <td>${Number(r.au_value).toFixed(4)}</td><td>${r.au_unit}</td></tr>`).join('');
}
document.getElementById('go').addEventListener('click', load);
boot();
