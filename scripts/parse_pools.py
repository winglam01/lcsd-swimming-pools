import json
import re
import sys
import unicodedata
from html import unescape
from pathlib import Path

BASE = Path(r"C:\Users\wingl\Documents\Minimax\lcsd-swimming-pool")
DATA = BASE / "data"


def to_text(html: str) -> str:
    if not html:
        return ""
    t = re.sub(r"(?is)<script.*?</script>", " ", html)
    t = re.sub(r"(?is)<style.*?</style>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(div|p|tr|li|h[1-6]|td|table)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = unescape(t)
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(\n[ ]*){2,}", "\n", t)
    return t.strip()


def parse_venues(path: Path, lang: str, name_key: str):
    content = path.read_text(encoding="utf-8", errors="replace")
    rows = re.findall(r"(?s)<tr>(.*?)</tr>", content)
    out = []
    for block in rows:
        m = re.search(r"Swimming\.do\?swpId=(\d+)", block)
        if not m:
            continue
        swp_id = m.group(1)
        nm = re.search(r'title="([^"]*?)"\s*>([^<]*?)</a>', block)
        if not nm:
            continue
        name = to_text(nm.group(1)).strip()
        if name_key not in name:
            continue

        fields = {}
        for fm in re.finditer(r'(?s)<div class="row content-row">(.*?)<div class="col-lg-10">(.*?)</div>\s*</div>', block):
            label = to_text(fm.group(1)).strip()
            value = to_text(fm.group(2)).strip()
            if label:
                fields.setdefault(label, value)

        tel = re.search(r'(?s)title="電話">\s*<p[^>]*>(.*?)</p>', block)
        mail = re.search(r"mailto:([^\"]+)", block)

        out.append(
            {
                "lang": lang,
                "swpId": swp_id,
                "name": name,
                "address": fields.get("地址", "") or fields.get("Address", ""),
                "hours": fields.get("每日開放時間", "") or fields.get("Daily Opening Hours", ""),
                "restDay": fields.get("休息日", "") or fields.get("Close on", "") or fields.get("Closure Day", ""),
                "fields": fields,
                "phone": to_text(tel.group(1)).strip() if tel else "",
                "email": mail.group(1) if mail else "",
            }
        )
    return out


tc = parse_venues(DATA / "phoneaddress_tc.html", "tc", "游泳池")
en = parse_venues(DATA / "phoneaddress_en.html", "en", "Swimming Pool")
print(f"TC pools: {len(tc)}   EN pools: {len(en)}", file=sys.stderr)

en_by_id = {p["swpId"]: p for p in en}
merged = []
for t in sorted(tc, key=lambda x: int(x["swpId"])):
    e = en_by_id.get(t["swpId"], {})
    merged.append(
        {
            "swpId": t["swpId"],
            "nameTC": t["name"],
            "nameEN": e.get("name", ""),
            "address": t["address"],
            "addressEN": e.get("address", ""),
            "hours": t["hours"],
            "hoursEN": e.get("hours", ""),
            "restDay": t["restDay"],
            "restDayEN": e.get("restDay", ""),
            "phone": t["phone"],
            "email": t["email"],
            "urlTC": f"https://www.lcsd.gov.hk/clpss/tc/webApp/Swimming.do?swpId={t['swpId']}",
            "urlEN": f"https://www.lcsd.gov.hk/clpss/en/webApp/Swimming.do?swpId={t['swpId']}",
        }
    )

(DATA / "pools.json").write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
for p in merged:
    print(f"{p['swpId']:>3}  {p['nameTC']:<12} {p['nameEN']}")
