# Automation

The public site must not depend on a person extracting each filing.

`python3 -m aurum refresh` indexes current and historical ESEF packages, converts euro line items to €Au, and writes `web/stocks-snapshot.json`.

GitHub Action `aurum-euro-refresh` runs that command every day at 05:20 UTC and publishes the snapshot on main.

The ENI worker at `/aurum-euro` reads that snapshot (cached a few hours). New packages appear after the next scheduled refresh, not after a manual paste.
