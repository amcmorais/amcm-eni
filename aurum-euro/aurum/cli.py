from __future__ import annotations
import argparse, json
from .store import connect, init_db
from .pipeline import rebuild, ingest_gold, ingest_nama_gdp
from .refresh import refresh_stocks


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aurum")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("rebuild")
    sub.add_parser("refresh")
    sub.add_parser("ingest-gold")
    g = sub.add_parser("ingest-eurostat")
    g.add_argument("--dataset", default="nama_10_gdp")
    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8091)
    args = p.parse_args(argv)
    if args.cmd == "init":
        con = connect(); init_db(con); con.close(); print("db ready"); return 0
    if args.cmd == "rebuild":
        print(json.dumps(rebuild(), indent=2)); return 0
    if args.cmd == "refresh":
        print(json.dumps(refresh_stocks(), indent=2)); return 0
    if args.cmd == "ingest-gold":
        con = connect(); init_db(con); n=ingest_gold(con); print("gold", n); return 0
    if args.cmd == "ingest-eurostat":
        con = connect(); init_db(con); ingest_gold(con); print(json.dumps(ingest_nama_gdp(con), indent=2)); return 0
    if args.cmd == "serve":
        import uvicorn
        uvicorn.run("aurum.api:app", host=args.host, port=args.port, reload=False)
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
