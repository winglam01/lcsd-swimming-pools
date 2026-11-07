"""Export the indoor-pool dataset as CSV (for spreadsheet use)."""

import csv
import json
from datetime import date
from pathlib import Path

BASE = Path(r"C:\Users\wingl\Documents\Minimax\lcsd-swimming-pool")
DATA = BASE / "data"
records = json.loads((DATA / "page_data.json").read_text(encoding="utf-8"))

STATUS_LABEL = {
    "open": "Open today (all sessions)",
    "evening": "Open evenings only today (daytime cleansing closure)",
    "closed": "Closed today (annual maintenance)",
}

# The status columns are a snapshot of the build date. The web page recomputes
# them live from the visitor's clock, so it never goes stale.
STATUS_AS_OF = date.today().isoformat()

rows = []
for r in records:
    indoor = "; ".join(
        f"{w['label']}: closes {w['start']}, reopens {w['reopen']}" for w in r["indoorWindows"])
    outdoor = "; ".join(
        f"{w['label']}: closes {w['start']}, reopens {w['reopen']}" for w in r["outdoorWindows"])
    rows.append({
        "Pool (EN)": r["nameEN"],
        "Pool (TC)": r["nameTC"],
        "Address": r["addr"],
        "Complex": r["typeLabel"],
        "Status today": STATUS_LABEL.get(r.get("status", ""), ""),
        "Status as of": STATUS_AS_OF,
        "Routine day off": r["day"],
        "Routine day off (TC)": r["dayTC"],
        "Closure time / note": " ".join((r["restDay"] or "").split()),
        "Indoor closure (annual maintenance)": indoor,
        "Indoor open period": r["openPeriod"],
        "Outdoor closure": outdoor,
        "Indoor facilities": " | ".join(r["indoorFacilities"][:6]),
        "Phone": r["phone"],
        "Email": r["email"],
        "LCSD page (EN)": r["url"],
        "LCSD page (TC)": r["urlTC"],
    })

out = DATA / "lcsd-indoor-pools.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out} ({len(rows)} rows)")
