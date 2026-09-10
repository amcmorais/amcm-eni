function formatContinental(n){
  const x = Number(n);
  if (!Number.isFinite(x)) return n;
  const sign = x < 0 ? "-" : "";
  const a = Math.abs(x);
  const [whole, frac] = a.toFixed(2).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return sign + grouped + "," + frac;
}
function formatAu(n){
  const x = Number(n);
  if (!Number.isFinite(x)) return "—";
  const sign = x < 0 ? "-" : "";
  const a = Math.abs(x);
  let coeff = a, name = "";
  if (a >= 1e18) { coeff = a/1e18; name = "trillion"; }
  else if (a >= 1e12) { coeff = a/1e12; name = "billion"; }
  else if (a >= 1e9) { coeff = a/1e9; name = "milliard"; }
  else if (a >= 1e6) { coeff = a/1e6; name = "million"; }
  return sign + formatContinental(coeff) + (name ? " " + name : "") + " €Au";
}
const $ = s => document.querySelector(s);
const fmt = formatContinental;
let SNAP = null;

function catalog(s){
  const raw = s.catalog || [];
  if (raw[0] && raw[0].geography_id) return raw;
  const keys = raw.map(r => typeof r === "string" ? r : r.id).filter(Boolean);
  const extra = Object.keys(s.observations || {});
  const all = [...new Set([...keys, ...extra])];
  return all.map(id => {
    const [ds, geoPart, ind] = String(id).split("|");
    const geo = (geoPart || "").replace("geo:", "");
    return {
      id, dataset_id: ds, dataset_title: ds,
      geography_id: geo, geography: geo,
      indicator_id: ind, indicator: ind
    };
  });
}
function available(s, geo, ind, ds){
  return catalog(s).filter(r =>
    (!geo || r.geography_id === geo) &&
    (!ind || ind === "*" || r.indicator_id === ind) &&
    (!ds || r.dataset_id === ds)
  );
}
async function snap(){
  if (SNAP) return SNAP;
  for (const u of ["/aurum-euro/snapshot.json", "snapshot.json"]) {
    try {
      const r = await fetch(u);
      if (r.ok) { SNAP = await r.json(); return SNAP; }
    } catch (e) {}
  }
  SNAP = { catalog: [], observations: {}, status: {} };
  return SNAP;
}
function fill(sel, rows, vk, lk, prefer){
  const cur = sel.value;
  sel.innerHTML = "";
  if (vk === "indicator_id") {
    const o = document.createElement("option");
    o.value = "*"; o.textContent = "All categories";
    sel.appendChild(o);
  }
  const seen = new Set();
  rows.forEach(r => {
    if (seen.has(r[vk])) return;
    seen.add(r[vk]);
    const o = document.createElement("option");
    o.value = r[vk];
    o.textContent = r[lk] || r[vk];
    sel.appendChild(o);
  });
  if (prefer && [...sel.options].some(o => o.value === prefer)) sel.value = prefer;
  else if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
}
function syncSelects(changed){
  const s = SNAP;
  const geo = $("#geo").value;
  const ind = $("#ind").value;
  const ds = $("#ds").value;
  if (changed === "geo") {
    fill($("#ind"), available(s, geo, null, null), "indicator_id", "indicator", "*");
    fill($("#ds"), available(s, geo, null, null), "dataset_id", "dataset_title");
  } else if (changed === "ds") {
    fill($("#ind"), available(s, geo, null, $("#ds").value), "indicator_id", "indicator", "*");
  } else {
    fill($("#geo"), catalog(s), "geography_id", "geography", "EA20");
    fill($("#ds"), available(s, $("#geo").value, null, null), "dataset_id", "dataset_title", "nama_10_gdp");
    fill($("#ind"), available(s, $("#geo").value, null, $("#ds").value), "indicator_id", "indicator", "*");
  }
}
function draw(){
  const s = SNAP;
  const geo = $("#geo").value;
  const ind = $("#ind").value;
  const ds = $("#ds").value;
  const rows = available(s, geo, ind === "*" ? null : ind, ds);
  const indicators = [];
  const seen = new Set();
  rows.forEach(r => {
    if (seen.has(r.indicator_id)) return;
    seen.add(r.indicator_id);
    indicators.push(r);
  });
  $("#series-id").textContent = rows.length
    ? (rows[0].geography + " — " + (rows[0].dataset_title || ds) + " — " + indicators.length + " categories in €Au")
    : "No published series matches this selection.";
  const byPeriod = {};
  rows.forEach(r => {
    const recs = (s.observations && s.observations[r.id]) || [];
    recs.forEach(o => {
      byPeriod[o.period] = byPeriod[o.period] || {};
      byPeriod[o.period][r.indicator_id] = o;
    });
  });
  const periods = Object.keys(byPeriod).sort();
  const thead = document.querySelector("#wide-head") || document.querySelector("thead tr");
  if (thead) {
    thead.innerHTML = "<th>Reference period</th>" + indicators.map(i =>
      `<th>${i.indicator || i.indicator_id} (€Au)</th>`).join("");
  }
  $("#tb").innerHTML = periods.length ? periods.map(p => {
    const cells = indicators.map(i => {
      const o = byPeriod[p][i.indicator_id];
      return `<td class="num">${o ? formatAu(o.au_value) : "—"}</td>`;
    }).join("");
    return `<tr><td>${p}</td>${cells}</tr>`;
  }).join("") : `<tr><td colspan="${1+indicators.length}">No Aurum Euro observations are published for this selection.</td></tr>`;
}
async function boot(){
  const s = await snap();
  const st = s.status || {};
  $("#stats").innerHTML = [
    ["Observations in Aurum Euro", st.au_observations],
    ["Published series", catalog(s).length],
    ["Gold prices used", st.gold_rows]
  ].map(([k,v]) => `<div class="card"><span>${k}</span><b>${fmt(v || 0)}</b></div>`).join("");
  if ($("#notice")) $("#notice").textContent = st.notice || "";
  syncSelects("init");
  ["geo","ind","ds"].forEach(id => {
    const el = $("#"+id);
    if (el) el.addEventListener("change", ev => { syncSelects(ev.target.id); draw(); });
  });
  draw();
}
boot();
