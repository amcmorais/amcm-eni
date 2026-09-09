
const $ = s => document.querySelector(s);
const fmt = n => {
  const x = Number(n);
  if (!Number.isFinite(x)) return n;
  return x.toLocaleString("en-GB", {maximumFractionDigits: 4});
};
let SNAP=null;
async function snap(){
  if (SNAP) return SNAP;
  for (const u of ["/aurum-euro/snapshot.json","snapshot.json"]) {
    try { const r=await fetch(u); if(r.ok){ SNAP=await r.json(); return SNAP; } } catch(e){}
  }
  throw new Error("The repository snapshot could not be read.");
}
function catalogs(s){
  const c=s.catalog||[];
  const uniq=(k)=>[...new Map(c.map(x=>[x[k],x])).values()];
  return {
    geo: uniq("geography_id").sort((a,b)=>a.geography.localeCompare(b.geography)),
    ind: uniq("indicator_id").sort((a,b)=>a.indicator.localeCompare(b.indicator)),
    ds: uniq("dataset_id").sort((a,b)=>a.dataset_title.localeCompare(b.dataset_title)),
  };
}
function fillSelect(sel, rows, valueKey, labelKey){
  sel.innerHTML="";
  rows.forEach(r=>{
    const o=document.createElement("option");
    o.value=r[valueKey]; o.textContent=r[labelKey];
    sel.appendChild(o);
  });
}
function currentId(s){
  const geo=$("#geo").value, ind=$("#ind").value, ds=$("#ds").value;
  const hit=(s.catalog||[]).find(x=>x.geography_id===geo && x.indicator_id===ind && x.dataset_id===ds);
  return hit && hit.id;
}
function rowsOf(s,id){ return (s.observations && s.observations[id]) || []; }
async function boot(){
  const s=await snap();
  const st=s.status||{};
  $("#stats").innerHTML = [
    ["Gold prices recorded", st.gold_rows],
    ["Original observations", st.source_observations],
    ["Observations in Aurum Euro", st.au_observations],
    ["Collections", (s.datasets||[]).length]
  ].map(([k,v])=>`<div class="card"><span>${k}</span><b>${fmt(v)}</b></div>`).join("");
  $("#notice").textContent = st.notice || "";
  const cat=catalogs(s);
  fillSelect($("#geo"), cat.geo, "geography_id", "geography");
  fillSelect($("#ind"), cat.ind, "indicator_id", "indicator");
  fillSelect($("#ds"), cat.ds, "dataset_id", "dataset_title");
  const prefG=cat.geo.find(x=>x.geography_id==="EA20"); if(prefG) $("#geo").value="EA20";
  const prefI=cat.ind.find(x=>x.indicator_id==="B1GQ"); if(prefI) $("#ind").value="B1GQ";
  document.getElementById("jsonld").textContent=JSON.stringify({
    "@context":"https://schema.org",
    "@type":"DataCatalog",
    "name":"Aurum Euro Repository",
    "url":"https://eni.calhegasmorais.pt/aurum-euro",
    "description":"European statistical observations preserved in the original unit and expressed in Aurum Euro.",
    "creator":{"@type":"Person","name":"André Manuel Calhegas Morais","url":"https://eni.calhegasmorais.pt/"},
    "measurementTechnique":"X_au = X_eur * 100 / P_gold_eur_per_troy_ounce",
    "variableMeasured":"€Au",
    "isAccessibleForFree": true
  });
  ["geo","ind","ds"].forEach(id=>$( "#"+id ).addEventListener("change", draw));
  draw();
}
function draw(){
  const s=SNAP;
  const id=currentId(s);
  $("#series-id").textContent = id ? ("Machine identifier: "+id) : "No series matches the selected territory, account and collection.";
  const rows=id?rowsOf(s,id):[];
  $("#tb").innerHTML = rows.length ? rows.map(r=>`<tr>
    <td>${r.period}</td>
    <td class="num">${fmt(r.source_value)}</td>
    <td>${r.source_unit}</td>
    <td class="num">${fmt(r.gold_price)}</td>
    <td>${String(r.gold_alignment_method||"").replaceAll("_"," ")}</td>
    <td class="num">${fmt(r.au_value)}</td>
    <td>${r.au_unit}</td>
  </tr>`).join("") : `<tr><td colspan="7">No observations are published for this selection.</td></tr>`;
  if(id){
    $("#json").href="/aurum-euro/snapshot.json";
    $("#csv").href="/aurum-euro/snapshot.json";
  }
}
boot();
