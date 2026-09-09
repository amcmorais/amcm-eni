"""Public API. Serve definition, gold, datasets, observations, status."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from .store import connect, init_db, DEFAULT_DB
from .definition import DEFINITION
from .pipeline import rebuild

WEB = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(title="Aurum Euro repository", version="0.1.0-lab")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db():
    con = connect()
    init_db(con)
    return con


@app.get("/api/v1/definition")
def definition():
    return DEFINITION


@app.get("/api/v1/health")
def health():
    con = db()
    gold_n = con.execute("SELECT COUNT(*) FROM gold_prices").fetchone()[0]
    au_n = con.execute("SELECT COUNT(*) FROM au_observations").fetchone()[0]
    raw_n = con.execute("SELECT COUNT(*) FROM observations_raw").fetchone()[0]
    last = con.execute("SELECT run_id, source, status, finished_at, observations_added FROM ingestion_runs ORDER BY started_at DESC LIMIT 1").fetchone()
    con.close()
    return {
        "status": "ok",
        "service": "aurum-euro",
        "gold_rows": gold_n,
        "source_observations": raw_n,
        "au_observations": au_n,
        "last_run": dict(last) if last else None,
    }


@app.get("/api/v1/gold")
def gold(frequency: str = "A"):
    con = db()
    rows = con.execute(
        "SELECT observation_date, frequency, price_eur_per_troy_oz, methodology, source FROM gold_prices WHERE frequency=? ORDER BY observation_date",
        (frequency,),
    ).fetchall()
    con.close()
    return {"unit": "EUR/troy oz Au 999.9", "frequency": frequency, "rows": [dict(r) for r in rows]}


@app.get("/api/v1/datasets")
def datasets():
    con = db()
    rows = con.execute("SELECT id, source_id, code, title, frequency FROM datasets").fetchall()
    con.close()
    return {"datasets": [dict(r) for r in rows]}


@app.get("/api/v1/status")
def status():
    return health()


@app.get("/api/v1/au/{dataset}")
def au_dataset(dataset: str, unit: str = Query("both", pattern="^(EUR|au|both)$")):
    con = db()
    q = """
    SELECT r.reference_period AS period,
           r.value AS source_value,
           r.unit AS source_unit,
           a.gold_price,
           a.gold_price_date_or_period,
           a.gold_alignment_method,
           a.derived_value AS au_value,
           a.derived_unit AS au_unit,
           a.transformation_version,
           a.au_definition_version
      FROM au_observations a
      JOIN observations_normalized n ON n.id = a.normalized_id
      JOIN observations_raw r ON r.id = n.raw_id
      JOIN dataset_versions v ON v.id = r.dataset_version_id
     WHERE v.dataset_id = ?
     ORDER BY r.reference_period
    """
    rows = [dict(x) for x in con.execute(q, (dataset,)).fetchall()]
    con.close()
    return {"dataset": dataset, "unit_mode": unit, "n": len(rows), "rows": rows}


@app.get("/api/v1/observations/{oid}")
def observation(oid: int):
    con = db()
    row = con.execute(
        """SELECT a.*, r.reference_period, r.value AS source_value, r.unit AS source_unit, r.entity_id, r.indicator_id
             FROM au_observations a
             JOIN observations_normalized n ON n.id=a.normalized_id
             JOIN observations_raw r ON r.id=n.raw_id
            WHERE a.id=?""",
        (oid,),
    ).fetchone()
    con.close()
    if not row:
        return JSONResponse({"error": "not found"}, status_code=404)
    return dict(row)


@app.post("/api/v1/rebuild")
def api_rebuild():
    return rebuild()


@app.get("/api/v1/download/{dataset}.json")
def dl_json(dataset: str):
    return au_dataset(dataset)


@app.get("/api/v1/download/{dataset}.csv")
def dl_csv(dataset: str):
    data = au_dataset(dataset)
    def gen():
        yield "period,source_value,source_unit,gold_price,gold_alignment,au_value,au_unit\n"
        for r in data["rows"]:
            yield f"{r['period']},{r['source_value']},{r['source_unit']},{r['gold_price']},{r['gold_alignment_method']},{r['au_value']},{r['au_unit']}\n"
    return StreamingResponse(gen(), media_type="text/csv")


@app.get("/")
def home():
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=str(WEB / "static")), name="static")
