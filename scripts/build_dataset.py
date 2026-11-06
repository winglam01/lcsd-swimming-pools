"""Build the final LCSD indoor-pool dataset.

Sources (fetched live from lcsd.gov.hk):
  - /clpss/tc|en/webApp/PhoneAddress.do  (Facilities & Venues search: hours, closure day)
  - /clpss/tc|en/webApp/Swimming.do?swpId=N  (per-pool detail: schedule, maintenance, cleaning day)

The indoor-pool closure windows below are curated from the LCSD per-pool pages and
verified against the raw page text by verify_against_source().
"""

import json
import re
import html as htmllib
from pathlib import Path

BASE = Path(r"C:\Users\wingl\Documents\Minimax\lcsd-swimming-pool")
DATA = BASE / "data"
PAGES = DATA / "pages"

# ---------------------------------------------------------------- curated data
# swpId: dict(indoor=[closure windows], outdoor=[closure windows] | None, note)
# window = (startISO, endISO, tcText, enText, facilitiesLabel)
M = "mixed"
I = "indoor_only"

CURATED = {
    1:  dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳館（整個泳池設施）")], outdoor=None),
    2:  dict(type=M, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "室內泳池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外泳池")]),
    3:  dict(type=I, indoor=[("2026-12-01", "2027-01-20", "1.12.2026 - 20.1.2027", "From 1 December to 20 January of the following year", "全泳池設施")], outdoor=None),
    4:  dict(type=M, indoor=[("2027-05-11", "2027-06-30", "5月11日至6月30日", "From 11 May to 30 June", "室內主池及訓練池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外習泳池及幼童池")]),
    5:  dict(type=I, indoor=[("2027-02-20", "2027-04-21", "2月20日至4月21日", "From 20 February to 21 April", "全泳池設施（冬季時間表列明 13.2.2027 – 14.4.2027）")], outdoor=None),
    6:  dict(type=I, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "全泳池設施")], outdoor=None),
    7:  dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳館")], outdoor=None),
    8:  dict(type=M, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "室內副池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "跳水池、訓練池、習泳池及戲水池"),
                      ("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "戶外主池（連同副池及跳水池）")]),
    9:  dict(type=I, indoor=[("2026-11-01", "2027-02-23", "11月1日至翌年2月23日", "From 1 November to 23 February of the following year", "除主池外，其他泳池"),
                             ("2027-02-24", "2027-04-15", "2月24日至4月15日", "From 24 February to 15 April", "全池")], outdoor=None),
    10: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    11: dict(type=M, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "室內泳池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外泳池")]),
    12: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "1.11.2026 - 31.3.2027", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    13: dict(type=M, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "室內泳池")],
             outdoor=[("2026-11-01", "2027-03-31", "1.11.2026 - 31.3.2027", "1.11.2026 - 31.3.2027", "戶外泳池（冬季開放時間表）"),
                      ("2027-04-01", "2027-04-15", "1.4.2027 - 15.4.2027", "1.4.2027 - 15.4.2027", "戶外泳池（冬季開放時間表）")]),
    14: dict(type=M, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "室內主池（由2027年開始）")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外泳池")]),
    15: dict(type=M, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "室內副池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外泳池")]),
    16: dict(type=M, indoor=[("2027-05-11", "2027-06-30", "5月11日至6月30日", "From 11 May to 30 June", "室內泳池（訓練池及嬉水池1）")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外泳池")]),
    17: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    18: dict(type=M, indoor=[("2027-01-02", "2027-02-21", "1月2日至2月21日", "From 2 January to 21 February", "室內泳池（主池及訓練池）")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "室外泳池")]),
    19: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    20: dict(type=M, indoor=[("2027-04-16", "2027-06-05", "2027年4月16日至2027年6月5日", "From 16 April 2027 to 5 Jun 2027", "室內泳池（主池、訓練池）")],
             outdoor=[("2026-11-01", "2027-04-15", "2026年11月1日至翌年4月15日", "From 1 November 2026 to 15 April of the following year", "戶外泳池（訓練池、習泳池、嬉水池及跳水池）")]),
    21: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施（十一月至三月暫停開放）")], outdoor=None),
    22: dict(type=I, indoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "副池、訓練池、跳水池及幼童池"),
                             ("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "主池")], outdoor=None),
    23: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    24: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    25: dict(type=M, indoor=[("2027-05-01", "2027-06-30", "5月1日至6月30日", "From 1 May to 30 June", "室內主池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外訓練池、習泳池及嬉水池")]),
    26: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    27: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    28: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    29: dict(type=I, indoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "副池、訓練池及戲水池"),
                             ("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "主池")], outdoor=None),
    30: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    31: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    32: dict(type=M, indoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "副池、兒童池、幼童池、訓練池及習泳池")],
             outdoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "主池"),
                      ("2026-11-01", "2027-06-05", "11月1日至翌年6月5日", "From 1 November to 5 June of the following year", "跳水池")]),
    33: dict(type=M, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "室內泳池（主池、按摩池）")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外泳池（訓練池、嬉水池）")]),
    34: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    35: dict(type=M, indoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "訓練池、習泳池、跳水池、戲水池及嬉水池"),
                             ("2027-05-04", "2027-06-23", "5月4日至6月23日", "From 4 May to 23 June", "主池")], outdoor=None),
    36: dict(type=I, indoor=[("2026-11-01", "2027-03-31", "11月1日至翌年3月31日", "From 1 November to 31 March of the following year", "全泳池設施")], outdoor=None),
    37: dict(type=I, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "全泳池設施")], outdoor=None),
    38: dict(type=M, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "主池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "訓練池")]),
    39: dict(type=I, indoor=[("2027-05-02", "2027-07-26", "5月2日至7月26日", "From 2 May to 26 July", "全泳池設施")], outdoor=None),
    40: dict(type=I, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "全泳池設施")], outdoor=None),
    41: dict(type=I, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "全泳池設施")], outdoor=None),
    42: dict(type=M, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "室內訓練池及習泳池")],
             outdoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "日光浴場（隨泳池維修）")]),
    43: dict(type=M, indoor=[("2026-09-01", "2026-10-21", "9月1日至10月21日", "1 September to 21 October", "室內訓練池、嬉水池及按摩池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "室外泳池（主池、訓練池及習泳池）")]),
    44: dict(type=I, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "全泳池設施")], outdoor=None),
    250: dict(type=I, indoor=[("2026-09-11", "2026-10-31", "9月11日至10月31日", "From 11 September to 31 October", "全泳池設施")], outdoor=None),
    261: dict(type=M, indoor=[("2027-04-16", "2027-06-05", "4月16日至6月5日", "From 16 April to 5 June", "室內訓練池及室內按摩池")],
             outdoor=[("2026-11-01", "2027-04-15", "11月1日至翌年4月15日", "From 1 November to 15 April of the following year", "戶外主池及戶外訓練池")]),
}

WEEKDAY_EN = {"一": "Monday", "二": "Tuesday", "三": "Wednesday", "四": "Thursday", "五": "Friday", "六": "Saturday", "日": "Sunday"}


def clean(s):
    if not s:
        return ""
    t = re.sub(r"(?is)<script.*?</script>", " ", s)
    t = re.sub(r"(?is)<style.*?</style>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(div|p|tr|li|h[1-6]|td|th|table)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = htmllib.unescape(t).replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(\n[ ]*){2,}", "\n", t)
    return t.strip()


def section_after_h4(c, heading, following_headings):
    """Slice the page from an <h4> heading up to the next <h4> heading."""
    m = re.search(r"<h4>\s*" + re.escape(heading) + r"\s*</h4>", c, re.I)
    if not m:
        return ""
    start = m.end()
    ends = []
    for f in following_headings:
        m2 = re.search(r"<h4>", c[start:], re.I)
        break
    m2 = re.search(r"<h4>.*?</h4>", c[start:], re.I | re.S)
    end = start + m2.start() if m2 else len(c)
    return c[start:end]


def get_field(c, labels):
    for lab in labels:
        m = re.search(r"(?s)<b>\s*(%s)\s*</b>\s*</td>\s*<td>(.*?)</td>" % "|".join([lab]), c)
        if m:
            return clean(m.group(2))
    return ""


def split_fac(fac):
    """Return (indoor_lines, outdoor_lines) honouring 室內設施/戶外設施 or 室內泳池/戶外泳池 labels."""
    if not fac:
        return [], []
    body = re.split(r"無障礙設施|無障礙設施：|公眾授泳區", fac)[0]
    m_in = re.search(r"(室內設施|室內泳池)\s*[:：]?", body)
    m_out = re.search(r"(戶外設施|戶外泳池|室外泳池)\s*[:：]?", body)
    lines = lambda s: [x.strip(" :") for x in re.split(r"\n+", s) if x.strip(" :")]
    if m_in and m_out and m_in.start() < m_out.start():
        return lines(body[m_in.end():m_out.start()]), lines(body[m_out.end():])
    if m_in:
        return lines(body[m_in.end():]), []
    if m_out:
        return [], lines(body[m_out.end():])
    return lines(body), []


def main():
    pools = json.loads((DATA / "pools.json").read_text(encoding="utf-8"))
    out = []
    warnings = []
    for p in pools:
        sid = p["swpId"]
        tc = (PAGES / f"pool_tc_{sid}.html").read_text(encoding="utf-8", errors="replace")
        en = (PAGES / f"pool_en_{sid}.html").read_text(encoding="utf-8", errors="replace")

        fac_tc = get_field(tc, ["設施"])
        fac_en = get_field(en, ["Facilities"])
        ind_tc, out_tc = split_fac(fac_tc)
        ind_en, out_en = split_fac(fac_en)

        # cleaning day + fallback
        sec_tc = clean(section_after_h4(tc, "每周大清潔行動", []))
        sec_en = clean(section_after_h4(en, "Weekly Cleansing Operation", []))
        m_day = re.search(r"逢星期([一二三四五六日])", sec_tc)
        m_alt = re.search(r"\((星期[一二三四五六日])\s*※\)", sec_tc)
        day_en = re.search(r"Every (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", sec_en)
        alt_en = re.search(r"\((Tuesday|Wednesday|Thursday|Friday|Monday|Saturday|Sunday)\s*※\)", sec_en)

        # indoor / outdoor facilities list (fallback: all listed facilities are indoor)
        cur = CURATED.get(int(sid))
        if cur is None:
            warnings.append(f"{sid}: no curated entry")
            continue

        indoor_fac = ind_tc or [x for x in (p.get("facilitiesRawTC") or "").split("\n")
                                if x.strip() and "無障礙" not in x and "公眾授泳區" not in x and "觀眾看台" not in x]
        outdoor_fac = out_tc

        # phone
        phone_tc = get_field(tc, ["電話號碼"])
        phone_en = get_field(en, ["Telephone"])

        # revision date
        rev_tc = get_field(tc, ["修訂日期"])
        m_rev = re.search(r"修訂日期[:：]\s*([^\n<]+)", tc)
        rev = clean(m_rev.group(1)) if m_rev else ""

        # verify curated dates appear in the source pages
        src_tc = clean(tc)
        src_en = clean(en)
        for w in cur["indoor"] + (cur["outdoor"] or []):
            tc_text = w[2].split("（")[0].split("(")[0].strip()
            en_text = w[3]
            if tc_text and not re.sub(r"\s", "", tc_text) in re.sub(r"\s", "", src_tc):
                warnings.append(f"{sid} {p['nameTC']}: TC date not found in page -> {tc_text}")
            if en_text and not re.sub(r"\s", "", en_text) in re.sub(r"\s", "", src_en):
                warnings.append(f"{sid} {p['nameTC']}: EN date not found in page -> {en_text}")

        rec = {
            "swpId": sid,
            "nameTC": p["nameTC"],
            "nameEN": p["nameEN"],
            "addressTC": p["address"],
            "addressEN": get_field(en, ["Address"]) or p.get("addressEN", ""),
            "phone": phone_tc or p.get("phone", ""),
            "email": p.get("email", ""),
            "urlTC": p["urlTC"],
            "urlEN": p["urlEN"],
            "type": cur["type"],
            "indoorFacilitiesTC": ind_tc,
            "indoorFacilitiesEN": ind_en,
            "outdoorFacilitiesTC": out_tc,
            "outdoorFacilitiesEN": out_en,
            "indoorClosure": cur["indoor"],
            "outdoorClosure": cur["outdoor"] or [],
            "cleanDayTC": m_day.group(1) if m_day else "",
            "cleanDayEN": day_en.group(1) if day_en else "",
            "cleanAltTC": m_alt.group(1) if m_alt else "",
            "cleanAltEN": alt_en.group(1) if alt_en else "",
            "restDayTC": p.get("restDay", ""),
            "restDayEN": p.get("restDayEN", "") or get_field(en, ["Close on", "Closure Day"]),
            "hoursTC": p.get("hours", ""),
            "hoursEN": p.get("hoursEN", "") or get_field(en, ["Daily Opening Hours"]),
            "maintenanceRawTC": clean(section_after_h4(tc, "配合每年維修工程的暫停開放時間", [])),
            "maintenanceRawEN": clean(section_after_h4(en, "Temporary Closure for Annual Maintenance", [])),
            "revisionDate": rev,
        }
        out.append(rec)

    (DATA / "final_pools.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"built {len(out)} pool records")
    if warnings:
        print(f"\n{len(warnings)} verification warnings:")
        for w in warnings:
            print("  !", w)
    else:
        print("all curated dates verified against source pages")


if __name__ == "__main__":
    main()
