
const $ = s => document.querySelector(s);
const fmt = n => {
  const x = Number(n);
  if (!Number.isFinite(x)) return n;
  return x.toLocaleString("en-GB", { maximumFractionDigits: 4 });
};
let SNAP = null;
async function snap() {
  if (SNAP) return SNAP;
  for (const u of ["/aurum-euro/snapshot.json", "snapshot.json"]) {
    try {
      const r = await fetch(u);
      if (r.ok) { SNAP = await r.json(); return SNAP; }
    } catch (e) {}
  }
  throw new Error("The repository snapshot could not be read.");
}
function catalog(s) { return s.catalog || []; }
function available(s, geo, ind, ds) {
  return catalog(s).filter(x =>
    (!geo || x.geography_id === geo) &&
    (!ind || x.indicator_id === ind) &&
    (!ds || x.dataset_id === ds)
  );
}
function fill(sel, rows, vk, lk, prefer) {
  const cur = sel.value;
  sel.innerHTML = "";
  const seen = new Set();
  rows.forEach(r => {
    if (seen.has(r[vk])) return;
    seen.add(r[vk]);
    const o = document.createElement("option");
    o.value = r[vk];
    o.textContent = r[lk];
    sel.appendChild(o);
  });
  if (prefer && [...sel.options].some(o => o.value === prefer)) sel.value = prefer;
  else if (cur && [...sel.options].some(o => o.value === cur)) sel.value = cur;
}
function syncSelects(changed) {
  const s = SNAP;
  const geo = $("#geo").value;
  const ind = $("#ind").value;
  const ds = $("#ds").value;
  if (changed === "geo") {
    fill($("#ind"), available(s, geo, null, null), "indicator_id", "indicator");
    fill($("#ds"), available(s, geo, $("#ind").value, null), "dataset_id", "dataset_title");
  } else if (changed === "ind") {
    fill($("#ds"), available(s, geo, $("#ind").value, null), "dataset_id", "dataset_title");
  } else if (changed === "ds") {
    fill($("#ind"), available(s, geo, null, $("#ds").value), "indicator_id", "indicator");
  } else {
    fill($("#geo"), catalog(s), "geography_id", "geography", "EA20");
    fill($("#ind"), available(s, $("#geo").value, null, null), "indicator_id", "indicator", "B1GQ");
    fill($("#ds"), available(s, $("#geo").value, $("#ind").value, null), "dataset_id", "dataset_title", "nama_10_gdp");
  }
}
function current() {
  const rows = available(SNAP, $("#geo").value, $("#ind").value, $("#ds").value);
  return rows[0] || null;
}
function draw() {
  const row = current();
  const id = row && row.id;
  $("#series-id").textContent = row
    ? (row.indicator + " — " + row.geography + " — " + row.dataset_title + "  ·  " + id)
    : "No published series matches this selection.";
  const recs = (id && SNAP.observations && SNAP.observations[id]) || [];
  $("#tb").innerHTML = recs.length ? recs.map(r => `<tr>
    <td>${r.period}</td>
    <td class="num">${fmt(r.source_value)}</td>
    <td>${r.source_unit}</td>
    <td class="num">${fmt(r.gold_price)}</td>
    <td>${String(r.gold_alignment_method || "").replaceAll("_", " ")}</td>
    <td class="num">${fmt(r.au_value)}</td>
    <td>${r.au_unit}</td>
  </tr>`).join("") : `<tr><td colspan="7">No observations are published for this selection.</td></tr>`;
}
async function boot() {
  const s = await snap();
  const st = s.status || {};
  $("#stats").innerHTML = [
    ["Gold prices recorded", st.gold_rows],
    ["Original observations", st.source_observations],
    ["Observations in Aurum Euro", st.au_observations],
    ["Published series", (s.catalog || []).length]
  ].map(([k, v]) => `<div class="card"><span>${k}</span><b>${fmt(v)}</b></div>`).join("");
  $("#notice").textContent = st.notice || "";
  syncSelects("init");
  ["geo", "ind", "ds"].forEach(id => {
    $("#" + id).addEventListener("change", ev => { syncSelects(ev.target.id); draw(); });
  });
  const el = document.getElementById("jsonld");
  if (el) el.textContent = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "DataCatalog",
    "name": "Aurum Euro Repository",
    "url": "https://eni.calhegasmorais.pt/aurum-euro",
    "numberOfItems": (s.catalog || []).length
  });
  draw();
}
boot();
