# Automation

`python3 -m aurum refresh` fetches Eurostat SDMX and ESEF packages, converts euro amounts to €Au on the long scale, and writes:

- web/accounts-snapshot.json
- web/stocks-snapshot.json

GitHub Action `aurum-euro-refresh` runs daily at 05:20 UTC and publishes those files on main. The public site reads them.

Long scale: million = 10^6; milliard = 10^9; billion = 10^12 = M^2; trillion = 10^18 = M^3.
