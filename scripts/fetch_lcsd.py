"""Fetch every LCSD public swimming pool page (TC + EN) into ./data/pages.

Run first, then build_dataset.py -> build_html.py.
    python scripts/fetch_lcsd.py
"""

import json
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
PAGES = DATA / "pages"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

INDEX_URLS = {
    "phoneaddress_tc": "https://www.lcsd.gov.hk/clpss/tc/webApp/PhoneAddress.do",
    "phoneaddress_en": "https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do",
}


def get(url, dest):
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"skip {dest.name}")
        return
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    dest.write_bytes(body)
    print(f"ok   {dest.name} ({len(body)} bytes)")


def main():
    PAGES.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    for name, url in INDEX_URLS.items():
        get(url, DATA / f"{name}.html")

    pools = json.loads((DATA / "pools.json").read_text(encoding="utf-8")) if (DATA / "pools.json").exists() else []
    if not pools:
        raise SystemExit("pools.json missing - run parse_pools.py first to seed the pool id list.")

    for p in pools:
        sid = p["swpId"]
        for lang in ("tc", "en"):
            get(f"https://www.lcsd.gov.hk/clpss/{lang}/webApp/Swimming.do?swpId={sid}",
                PAGES / f"pool_{lang}_{sid}.html")
            time.sleep(0.25)


if __name__ == "__main__":
    main()
