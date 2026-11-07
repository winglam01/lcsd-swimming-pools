"""Render the LCSD indoor swimming pool page (index.html) from final_pools.json."""

import json
import html
import re
from datetime import date, timedelta
from pathlib import Path

BASE = Path(r"C:\Users\wingl\Documents\Minimax\lcsd-swimming-pool")
DATA = BASE / "data"
OUT = BASE / "site"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
WD_ZH = {"Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三", "Thursday": "星期四",
         "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"}
# cycle order: 1 Nov -> 31 Oct
CYCLE = [10, 11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


def d(iso):
    y, m, dd = (int(x) for x in iso.split("-"))
    return date(y, m, dd)


def fmt(dt):
    return f"{dt.day} {MONTHS[dt.month - 1]} {dt.year}"


def fmt_md(dt):
    return f"{dt.day} {MONTHS[dt.month - 1]}"


def next_occurrence(start, end, today):
    """Next future instance of an annual window (start..end, inclusive)."""
    for year in range(today.year - 1, today.year + 3):
        s = start.replace(year=year)
        e = end.replace(year=year if end.month >= start.month else year)
        if end.month < start.month:
            e = end.replace(year=year + 1)
        if e >= today:
            return s, e
    return start, end


def map_into_cycle(iso, cycle_start_year):
    """Map an ISO date into the Nov->Oct cycle year (Sept/Oct -> later year)."""
    dt = d(iso)
    if dt.month >= 9 and dt.month <= 10:
        return dt.replace(year=cycle_start_year + 1)
    if dt.month >= 11:
        return dt.replace(year=cycle_start_year)
    return dt.replace(year=cycle_start_year + 1)


def open_periods(windows, cycle_start, cycle_end):
    """Exact-date complement of the closure windows inside the Nov->Oct cycle."""
    spans = []
    for w in windows:
        s = map_into_cycle(w[0], cycle_start.year)
        e = map_into_cycle(w[1], cycle_start.year)
        if e < s:
            e = e.replace(year=e.year + 1)
        spans.append((max(s, cycle_start), min(e, cycle_end)))
    spans = [sp for sp in spans if sp[0] <= sp[1]]
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out, prev = [], cycle_start
    for s, e in merged:
        if s > prev:
            out.append((prev, s - timedelta(days=1)))
        prev = max(prev, e + timedelta(days=1))
    if prev <= cycle_end:
        out.append((prev, cycle_end))
    return out


def fmt_range(a, b):
    if a.year == b.year:
        return f"{a.day} {MONTHS[a.month-1]} – {b.day} {MONTHS[b.month-1]} {b.year}"
    return f"{fmt(a)} – {fmt(b)}"


def esc(s):
    return html.escape(str(s if s is not None else ""))


def clean_lines(txt):
    return [l.strip() for l in (txt or "").split("\n") if l.strip()]


LABEL_NOISE = {"indoor facilities", "outdoor facilities", "accessible facilities",
               "室內設施", "戶外設施", "無障礙設施", "室內泳池", "戶外泳池"}


def strip_labels(lines):
    out = []
    for l in lines:
        key = l.strip(" :").lower()
        if key in LABEL_NOISE:
            continue
        if "barrier free" in key.lower() and len(l) > 120:
            continue
        out.append(l)
    return out


def md_of(iso):
    dt = d(iso)
    return (dt.month, dt.day)


def in_annual_window(today, start_iso, end_iso):
    """True if today falls inside the recurring annual closure window."""
    sm, sd = md_of(start_iso)
    em, ed = md_of(end_iso)
    tm, td = today.month, today.day
    tmd = (tm, td)
    if (sm, sd) <= (em, ed):
        return (sm, sd) <= tmd <= (em, ed)
    return tmd >= (sm, sd) or tmd <= (em, ed)


def build():
    pools = json.loads((DATA / "final_pools.json").read_text(encoding="utf-8"))
    captured = date(2026, 11, 6)          # when the LCSD pages were scraped
    today = date.today()                   # day the page is built for (JS keeps it live)
    today_wd = WD[today.weekday()]
    live_today = today

    records = []
    for p in pools:
        s = d(p["indoorClosure"][0][0])
        e = d(p["indoorClosure"][0][1])
        ns, ne = next_occurrence(s, e, today)
        reopen = ne + timedelta(days=1)
        windows = []
        for w in p["indoorClosure"]:
            ws, we = d(w[0]), d(w[1])
            nws, nwe = next_occurrence(ws, we, today)
            windows.append({
                "label": w[4],
                "tc": w[2],
                "en": w[3],
                "start": fmt(nws),
                "end": fmt(nwe),
                "reopen": fmt(nwe + timedelta(days=1)),
                "iso": w[0],
            })
        outdoor = []
        for w in p["outdoorClosure"]:
            ws, we = d(w[0]), d(w[1])
            nws, nwe = next_occurrence(ws, we, today)
            outdoor.append({"label": w[4], "start": fmt(nws), "end": fmt(nwe), "reopen": fmt(nwe + timedelta(days=1))})

        day = p["cleanDayEN"] or ""
        cleansing_today = day == today_wd
        maintenance_today = any(in_annual_window(today, w[0], w[1]) for w in p["indoorClosure"])
        if maintenance_today:
            status = "closed"
        elif cleansing_today:
            status = "evening"
        else:
            status = "open"
        window_md = [[md_of(w[0]), md_of(w[1])] for w in p["indoorClosure"]]
        records.append({
            "id": p["swpId"],
            "nameEN": p["nameEN"],
            "nameTC": p["nameTC"],
            "addr": p["addressEN"] or p["addressTC"],
            "addrTC": p["addressTC"],
            "phone": p["phone"],
            "email": p["email"],
            "url": p["urlEN"],
            "urlTC": p["urlTC"],
            "type": p["type"],
            "typeLabel": "Indoor only" if p["type"] == "indoor_only" else "Indoor + outdoor",
            "day": day,
            "dayTC": WD_ZH.get(day, ""),
            "dayIdx": WD.index(day) if day in WD else -1,
            "closedToday": cleansing_today,
            "restDay": p["restDayEN"] or p["restDayTC"],            "indoorWindows": windows,
            "outdoorWindows": outdoor,
            "openPeriod": ", ".join(fmt_range(a, b) for a, b in
                                   open_periods([(w[0], w[1]) for w in p["indoorClosure"]],
                                                date(2026, 11, 1), date(2027, 10, 31))),
            "indoorFacilities": p["indoorFacilitiesEN"] or p["indoorFacilitiesTC"],
            "indoorFacilitiesTC": p["indoorFacilitiesTC"],
            "outdoorFacilities": p["outdoorFacilitiesEN"] or p["outdoorFacilitiesTC"],
            "hours": p["hoursEN"] or p["hours"],
            "hoursTC": p["hoursTC"],
            "maintEN": p["maintenanceRawEN"],
            "maintTC": p["maintenanceRawTC"],
            "revision": p["revisionDate"],
            "search": f"{p['nameEN']} {p['nameTC']} {p['addressEN']} {p['addressTC']}".lower(),
            "status": status,
            "cleansingToday": cleansing_today,
            "maintenanceToday": maintenance_today,
            "windowMD": window_md,
        })

    records.sort(key=lambda r: (r["dayIdx"], r["nameEN"]))

    # ---- cards
    def window_list(items, cls):
        if not items:
            return ""
        rows = []
        for w in items:
            rows.append(
                f'<div class="wrow {cls}"><span class="wlabel">{esc(w["label"])}</span>'
                f'<span class="wdate"><b>Closes</b> {esc(w["start"])} <span class="arrow">→</span> <b>Reopens</b> {esc(w["reopen"])}</span>'
                f'<span class="wraw">LCSD: {esc(w.get("tc", ""))}</span></div>')
        return "".join(rows)

    cards = []
    for r in records:
        if r["status"] == "closed":
            status_badge = ('<span class="badge statusbadge closed">Closed today &middot; annual maintenance</span>')
        elif r["status"] == "evening":
            status_badge = '<span class="badge statusbadge evening">Open evenings only today</span>'
        else:
            status_badge = '<span class="badge statusbadge opentoday">Open today</span>'
        facs = "".join(f"<li>{esc(x)}</li>" for x in strip_labels(r["indoorFacilities"])[:6]) or "<li>—</li>"
        outf = "".join(f"<li>{esc(x)}</li>" for x in strip_labels(r["outdoorFacilities"])[:4])
        maint_tc = "<br>".join(esc(x) for x in clean_lines(r["maintTC"]))
        maint_en = "<br>".join(esc(x) for x in clean_lines(r["maintEN"]))
        hours = "<br>".join(esc(x) for x in clean_lines(r["hours"]))
        card = f"""
<article class="card" data-type="{r['type']}" data-day="{r['dayIdx']}" data-status="{r['status']}"
         data-clean="{r['dayIdx']}" data-win="{esc(json.dumps(r['windowMD'], separators=(',', ':')))}" data-name="{esc(r['search'])}">
  <header class="card-head">
    <div class="ctitle">
      <h3>{esc(r['nameEN'])}</h3>
      <p class="zh">{esc(r['nameTC'])}</p>
    </div>
    <div class="cbadges">
      <span class="badge day">Day off: {esc(r['day'])}</span>
      <span class="badge type">{esc(r['typeLabel'])}</span>
      {status_badge}
    </div>
  </header>
  <p class="addr">{esc(r['addr'])}</p>

  <div class="dayoff">
    <div class="dayoff-label">Routine day off / 每周大清潔日</div>
    <div class="dayoff-main">{esc(r['day'])} <span class="zh">{esc(r['dayTC'])}</span></div>
    <div class="dayoff-note">{esc(r['restDay'])}</div>
  </div>

  <div class="dates">
    <div class="dblock">
      <div class="dtitle">Indoor pool closure — annual maintenance / 室內泳池年度維修</div>
      {window_list(r['indoorWindows'], 'in')}
      <div class="openline">Indoor open period: <b>{esc(r['openPeriod'])}</b></div>
    </div>
    {f'<div class="dblock alt"><div class="dtitle">Outdoor pool closure (context)</div>{window_list(r["outdoorWindows"], "out")}</div>' if r['outdoorWindows'] else ''}
  </div>

  <details>
    <summary>Details — facilities, hours, LCSD wording</summary>
    <div class="detail-grid">
      <div>
        <h4>Indoor facilities / 室內設施</h4>
        <ul class="fac">{facs}</ul>
        {f'<h4>Outdoor facilities / 戶外設施</h4><ul class="fac">{outf}</ul>' if outf else ''}
        <h4>Contact</h4>
        <p class="small">{esc(r['phone'])} &middot; {esc(r['email'])}</p>
      </div>
      <div>
        <h4>Opening hours / 每日開放時間</h4>
        <p class="small">{hours}</p>
        <h4>LCSD annual maintenance wording</h4>
        <p class="small">{maint_en}</p>
        <p class="small zh">{maint_tc}</p>
      </div>
    </div>
    <p class="small links">
      <a href="{esc(r['url'])}" target="_blank" rel="noopener">LCSD page (EN)</a> &middot;
      <a href="{esc(r['urlTC'])}" target="_blank" rel="noopener">康文署頁面(中)</a>
      {f'&middot; <span class="rev">Page revised: {esc(r["revision"])}</span>' if r['revision'] else ''}
    </p>
  </details>
</article>"""
        cards.append(card)

    # ---- weekday summary
    by_day = {}
    for r in records:
        by_day.setdefault(r["day"], []).append(r)
    day_rows = []
    for day in WD:
        lst = by_day.get(day, [])
        names = "、".join(x["nameEN"] for x in lst) if lst else "—"
        zh = WD_ZH[day]
        day_rows.append(
            f'<tr><th scope="row"><a href="#day-{WD.index(day)}">{esc(day)}</a><span class="zh">{esc(zh)}</span></th>'
            f'<td class="cnt">{len(lst)}</td><td class="names">{esc(names)}</td></tr>')

    stats = {
        "total": len(records),
        "indoor_only": sum(1 for r in records if r["type"] == "indoor_only"),
        "mixed": sum(1 for r in records if r["type"] == "mixed"),
        "open_today": sum(1 for r in records if r["status"] in ("open", "evening")),
        "open_all_day": sum(1 for r in records if r["status"] == "open"),
        "evening_only": sum(1 for r in records if r["status"] == "evening"),
        "closed_today": sum(1 for r in records if r["status"] == "closed"),
    }
    day_counts = {day: len(by_day.get(day, [])) for day in WD}
    busiest = max(day_counts, key=lambda k: day_counts[k])

    chips = "".join(
        f'<button class="chip" data-day="{i}">{esc(d)}<span class="n">{day_counts[d]}</span></button>'
        for i, d in enumerate(WD))

    page = TEMPLATE
    for key, val in (
        ("stats_total", stats["total"]), ("stats_indoor", stats["indoor_only"]), ("stats_mixed", stats["mixed"]),
        ("stats_today", stats["open_today"]), ("stats_open_all", stats["open_all_day"]),
        ("stats_evening", stats["evening_only"]), ("stats_maint", stats["closed_today"]),
        ("today_long", f"{today.day} {MONTHS[today.month-1]} {today.year}"),
        ("captured", f"{captured.day} {MONTHS[captured.month-1]} {captured.year}"),
        ("today_wd", today_wd), ("busiest", busiest), ("chips", chips), ("cards", "".join(cards)),
        ("day_rows", "".join(day_rows)), ("day_names", "".join(f'<option value="{i}">{esc(dd)}</option>' for i, dd in enumerate(WD))),
        ("revision", records[0]["revision"] if records else ""),
    ):
        page = page.replace("%%" + key + "%%", str(val))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    (DATA / "page_data.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'index.html'}")
    print(f"  pools: {stats['total']}  indoor-only: {stats['indoor_only']}  mixed: {stats['mixed']}")
    print(f"  today ({today_wd}): open all day {stats['open_all_day']}, evenings only {stats['evening_only']}, "
          f"closed for maintenance {stats['closed_today']}, open today total {stats['open_today']}")

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LCSD Indoor Swimming Pools — Routine Day Off, Opening &amp; Closing Dates</title>
<meta name="description" content="All 46 LCSD public swimming pools in Hong Kong: routine weekly day off, indoor pool annual maintenance closing and reopening dates, opening hours. Source: Leisure and Cultural Services Department.">
<style>
:root{
  --bg:#0d1420; --panel:#151f30; --panel2:#1b2739; --line:#27344a; --txt:#e8eef8; --muted:#93a3bb;
  --blue:#4da3ff; --cyan:#3fd0c9; --amber:#ffb454; --red:#ff7a7a; --green:#5ddc9a;
}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0b111c 0%,#0d1420 30%,#0d1420 100%);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue","PingFang HK","Microsoft JhengHei",sans-serif;
  line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
a{color:var(--blue);text-decoration:none} a:hover{text-decoration:underline}
.zh{color:var(--muted);font-size:.82em;font-weight:400}
header.hero{background:linear-gradient(135deg,#10233d 0%,#123047 45%,#0e2a33 100%);
  border-bottom:1px solid var(--line);padding:46px 0 34px}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--cyan);font-weight:700}
h1{font-size:clamp(26px,4.4vw,44px);margin:10px 0 8px;line-height:1.12;letter-spacing:-.02em}
.sub{color:#b8c8dd;max-width:800px;font-size:16px;margin:0 0 6px}
.meta{color:var(--muted);font-size:13.5px;margin-top:14px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:26px}
.stat{background:rgba(255,255,255,.045);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat b{display:block;font-size:28px;line-height:1.1;color:#fff}
.stat span{font-size:12.5px;color:var(--muted)}
section{padding:34px 0}
h2{font-size:21px;margin:0 0 6px;letter-spacing:-.01em}
.lede{color:var(--muted);font-size:14.5px;margin:0 0 18px;max-width:900px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
thead th{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700}
tbody th{font-weight:600;white-space:nowrap} .cnt{color:var(--cyan);font-weight:700;width:52px}
.names{color:#c3d0e2;font-size:13.5px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:8px}
input[type=search],select{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:9px;
  padding:9px 12px;font-size:14px;font-family:inherit}
input[type=search]{min-width:250px;flex:1 1 260px}
.chip{background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:999px;padding:6px 13px;
  font-size:13px;cursor:pointer;font-family:inherit;display:inline-flex;gap:7px;align-items:center}
.chip:hover{border-color:var(--blue)} .chip.on{background:var(--blue);border-color:var(--blue);color:#04121f;font-weight:600}
.chip .n{background:rgba(255,255,255,.12);border-radius:999px;padding:1px 7px;font-size:11.5px}
.chip.on .n{background:rgba(0,0,0,.18)}
.chip.toggle{border-color:rgba(93,220,154,.35);color:#b6f0d0}
.chip.toggle:hover{border-color:var(--green)}
#openToday.on{background:var(--green);border-color:var(--green);color:#04231a;font-weight:700}
#fullToday.on{background:var(--cyan);border-color:var(--cyan);color:#032420;font-weight:700}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:16px;margin-top:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 18px 14px}
.card.hidden{display:none}
.card-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
.ctitle h3{margin:0;font-size:17px;letter-spacing:-.01em}
.ctitle .zh{margin:2px 0 0;font-size:13px}
.cbadges{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.badge{font-size:11.5px;padding:3px 9px;border-radius:999px;border:1px solid var(--line);background:var(--panel2);color:var(--muted);white-space:nowrap}
.badge.day{color:var(--cyan);border-color:rgba(63,208,201,.35)}
.badge.type{color:#a9c4e8}
.badge.closed{background:rgba(255,122,122,.14);border-color:rgba(255,122,122,.4);color:var(--red);font-weight:600}
.badge.evening{background:rgba(255,180,84,.13);border-color:rgba(255,180,84,.38);color:var(--amber);font-weight:600}
.badge.opentoday{background:rgba(93,220,154,.12);border-color:rgba(93,220,154,.38);color:var(--green);font-weight:600}
.addr{color:var(--muted);font-size:13px;margin:8px 0 12px}
.dayoff{background:var(--panel2);border:1px solid var(--line);border-left:3px solid var(--cyan);border-radius:10px;padding:10px 13px;margin-bottom:12px}
.dayoff-label{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.dayoff-main{font-size:20px;font-weight:700;margin:2px 0 3px}
.dayoff-note{font-size:12.5px;color:var(--muted);white-space:pre-line}
.dblock{margin-bottom:10px}
.dblock.alt{border-top:1px dashed var(--line);padding-top:10px}
.dtitle{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:7px;font-weight:700}
.wrow{display:grid;grid-template-columns:1fr;gap:2px;padding:8px 11px;border-radius:9px;margin-bottom:7px;
  background:rgba(255,180,84,.08);border:1px solid rgba(255,180,84,.22)}
.wrow.out{background:rgba(93,220,154,.07);border-color:rgba(93,220,154,.2)}
.wlabel{font-size:13.5px;font-weight:600;color:#ffd9a6}
.wrow.out .wlabel{color:#b6f0d0}
.wdate{font-size:13.5px} .wdate b{color:var(--muted);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;margin-right:3px}
.arrow{color:var(--muted);margin:0 4px}
.wraw{font-size:11.5px;color:var(--muted)}
.openline{font-size:13px;color:#c3d0e2;margin-top:6px} .openline b{color:var(--green)}
details{margin-top:10px;border-top:1px solid var(--line);padding-top:9px}
summary{cursor:pointer;font-size:13px;color:var(--blue);font-weight:600;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸ ";color:var(--muted)}
details[open] summary::before{content:"▾ "}
.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:10px}
@media(max-width:620px){.detail-grid{grid-template-columns:1fr}}
.detail-grid h4{margin:10px 0 4px;font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
ul.fac{margin:0;padding-left:17px;color:#c3d0e2;font-size:13px}
.small{font-size:12.5px;color:#c3d0e2;margin:0 0 6px;white-space:pre-line}
.small.zh{color:var(--muted)}
.links{margin-top:10px;padding-top:9px;border-top:1px dashed var(--line)}
.rev{color:var(--muted)}
footer{border-top:1px solid var(--line);margin-top:20px;padding:26px 0 40px;color:var(--muted);font-size:13px}
.note{background:rgba(77,163,255,.07);border:1px solid rgba(77,163,255,.25);border-radius:12px;padding:14px 16px;font-size:13.5px;color:#c3d0e2;margin-bottom:18px}
.foot-links a{margin-right:14px}
@media print{
  body{background:#fff;color:#111} header.hero{background:#fff;border-color:#999} .controls,.chips{display:none}
  .panel,.card,.stat{background:#fff;border-color:#ccc} .badge,.wrow{background:#fff;border-color:#999}
  .dayoff-note,.addr,.wraw,.zh,.lede{color:#444} a{color:#06c}
}
</style>
</head>
<body>
<header class="hero">
  <div class="wrap">
    <div class="eyebrow">Leisure and Cultural Services Department &middot; 康樂及文化事務署</div>
    <h1>LCSD Public Swimming Pools — Indoor Pool Routine Day Off, Opening &amp; Closing Dates</h1>
    <p class="sub">Every LCSD public swimming pool in Hong Kong, with the <b>routine weekly day off</b> (weekly cleansing day),
    the <b>indoor pool annual maintenance closing date</b> and the <b>reopening date</b>, plus the outdoor closures that affect
    what is actually open on the day.</p>
    <p class="meta">Data captured from lcsd.gov.hk on <b>%%captured%%</b> &middot; LCSD page revision: %%revision%%
      &middot; <span id="todayline">Today is %%today_wd%% — %%stats_today%% of %%stats_total%% pools have an open indoor pool</span></p>
    <div class="stats">
      <div class="stat"><b>%%stats_total%%</b><span>public pools listed</span></div>
      <div class="stat"><b id="statOpenToday">%%stats_today%%</b><span>open today (indoor pool)</span></div>
      <div class="stat"><b id="statOpenAll">%%stats_open_all%%</b><span>open all day today</span></div>
      <div class="stat"><b id="statEvening">%%stats_evening%%</b><span>evening session only today</span></div>
      <div class="stat"><b id="statMaint">%%stats_maint%%</b><span>closed today (maintenance)</span></div>
      <div class="stat"><b>%%stats_indoor%%</b><span>indoor-only complexes</span></div>
      <div class="stat"><b>%%stats_mixed%%</b><span>indoor + outdoor complexes</span></div>
    </div>
  </div>
</header>

<main>
<section class="wrap">
  <h2>How to read this page</h2>
  <p class="lede">LCSD operates a two-tier calendar: a <b>weekly</b> cleansing closure (the routine “day off”, normally from 10:00 a.m. to
  the end of the second session, moved to another day in the same week if it lands on a public holiday) and an <b>annual</b> maintenance
  closure that takes the indoor (and/or outdoor) pools out of service. Both are listed per pool below.</p>
  <div class="note">
    <b>Reading the dates.</b> “Closes → Reopens” is the indoor pool’s annual maintenance window: the date the indoor pool stops
    opening, and the date it opens again. “Indoor open period” is the complementary part of the year. Where a complex has both indoor and
    outdoor pools, the outdoor window is shown as well, because a closed outdoor pool often means “indoor only” even though the indoor
    pool itself is open.
  </div>
  <div class="note">
    <b>“Open today”.</b> Two filters answer “can I swim today?”.
    <b>Open today</b> keeps every pool with at least one open session today — including pools whose daytime session is shut for the weekly
    cleansing but that reopen for the evening session.
    <b>Open all day today</b> keeps only pools with no closure of any kind today.
    Pools closed for annual maintenance are excluded from both. The badge on each card spells out which case applies.
  </div>
</section>

<section class="wrap">
  <h2>Routine day off by weekday</h2>
  <p class="lede">Pools grouped by their weekly cleansing day. %%busiest%% is the most common day off.</p>
  <div class="panel">
    <table>
      <thead><tr><th>Weekday</th><th>Pools</th><th>Names</th></tr></thead>
      <tbody>%%day_rows%%</tbody>
    </table>
  </div>
</section>

<section class="wrap">
  <h2>All pools</h2>
  <p class="lede">Filter by name, weekday, pool type — or by what is actually open today.</p>
  <div class="controls">
    <input type="search" id="q" placeholder="Search pool name or address…" aria-label="Search">
    <select id="day" aria-label="Filter by weekday"><option value="">Any weekday</option>%%day_names%%</select>
    <select id="type" aria-label="Filter by type">
      <option value="">All pool types</option>
      <option value="indoor_only">Indoor only</option>
      <option value="mixed">Indoor + outdoor</option>
    </select>
    <button class="chip toggle" id="openToday" type="button" aria-pressed="false">Open today <span class="n" id="openTodayN">%%stats_today%%</span></button>
    <button class="chip toggle" id="fullToday" type="button" aria-pressed="false">Open all day today <span class="n" id="fullTodayN">%%stats_open_all%%</span></button>
    <button class="chip" id="reset" type="button">Reset</button>
  </div>
  <div class="chips" id="chips">%%chips%%</div>
  <div class="grid" id="grid">%%cards%%</div>
  <p class="lede" id="count"></p>
</section>
</main>

<footer class="wrap">
  <p><b>Source.</b> Leisure and Cultural Services Department (康樂及文化事務署) — <span class="foot-links">
    <a href="https://www.lcsd.gov.hk/en/facilities/facilitieslist.html" target="_blank" rel="noopener">List of Facilities &amp; Venues</a>
    <a href="https://www.lcsd.gov.hk/clpss/en/webApp/Swimming.do" target="_blank" rel="noopener">Public Swimming Pools</a>
    <a href="https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do" target="_blank" rel="noopener">Facilities &amp; Venues Search</a>
  </span></p>
  <p>Every row is linked back to the pool’s own LCSD page. Opening hours and closures are subject to change — the LCSD page and the
  pool office (phone shown on each card) are authoritative. This page is an unofficial convenience summary.</p>
  <p>Built with data captured %%captured%%. “Today” status is recomputed live in your browser from the current date.</p>
</footer>

<script>
(function () {
  const cards = Array.from(document.querySelectorAll('#grid .card'));
  const q = document.getElementById('q');
  const day = document.getElementById('day');
  const type = document.getElementById('type');
  const chips = Array.from(document.querySelectorAll('#chips .chip'));
  const count = document.getElementById('count');
  const openToday = document.getElementById('openToday');
  const fullToday = document.getElementById('fullToday');
  let chipDay = null;
  let onlyOpenToday = false;
  let onlyFullToday = false;

  const WD = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

  // Live "today" status, recomputed from the visitor's clock so the page never goes stale.
  function computeLiveStatus() {
    const now = new Date();
    const todayIdx = (now.getDay() + 6) % 7;          // 0 = Monday, matching the data
    const md = (now.getMonth() + 1) * 100 + now.getDate();
    const tally = { open: 0, evening: 0, closed: 0 };
    cards.forEach(c => {
      const windows = JSON.parse(c.dataset.win || '[]');
      let inMaintenance = false;
      windows.forEach(w => {
        const s = w[0][0] * 100 + w[0][1];
        const e = w[1][0] * 100 + w[1][1];
        if (s <= e ? (md >= s && md <= e) : (md >= s || md <= e)) inMaintenance = true;
      });
      const isCleansing = Number(c.dataset.clean) === todayIdx;
      let st = 'open';
      if (inMaintenance) st = 'closed';
      else if (isCleansing) st = 'evening';
      c.dataset.status = st;
      tally[st]++;
      const badge = c.querySelector('.statusbadge');
      if (badge) {
        badge.className = 'badge statusbadge ' + (st === 'closed' ? 'closed' : st === 'evening' ? 'evening' : 'opentoday');
        badge.textContent = st === 'closed' ? 'Closed today \\u00b7 annual maintenance'
                        : st === 'evening' ? 'Open evenings only today' : 'Open today';
      }
    });
    const openTotal = tally.open + tally.evening;
    document.getElementById('statOpenToday').textContent = openTotal;
    document.getElementById('statOpenAll').textContent = tally.open;
    document.getElementById('statEvening').textContent = tally.evening;
    document.getElementById('statMaint').textContent = tally.closed;
    document.getElementById('openTodayN').textContent = openTotal;
    document.getElementById('fullTodayN').textContent = tally.open;
    document.getElementById('todayline').textContent =
      'Today is ' + WD[todayIdx] + ' ' + now.getDate() + ' ' + MONTHS[now.getMonth()] + ' — ' +
      openTotal + ' of ' + cards.length + ' pools have an open indoor pool';
  }

  function apply() {
    const term = q.value.trim().toLowerCase();
    const dsel = day.value;
    const tsel = type.value;
    let shown = 0;
    cards.forEach(c => {
      const okQ = !term || c.dataset.name.includes(term);
      const okD = (!dsel && chipDay === null) || (dsel !== '' ? c.dataset.day === dsel : c.dataset.day === String(chipDay));
      const okT = !tsel || c.dataset.type === tsel;
      const st = c.dataset.status;
      const okOpen = !onlyOpenToday ? true : (st === 'open' || st === 'evening');
      const okFull = !onlyFullToday ? true : (st === 'open');
      const vis = okQ && okD && okT && okOpen && okFull;
      c.classList.toggle('hidden', !vis);
      if (vis) shown++;
    });
    count.textContent = 'Showing ' + shown + ' of ' + cards.length + ' pools.';
  }

  function toggle(btn, key) {
    const on = btn.classList.toggle('on');
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    if (key === 'open') { onlyOpenToday = on; if (on) { onlyFullToday = false; fullToday.classList.remove('on'); fullToday.setAttribute('aria-pressed','false'); } }
    else { onlyFullToday = on; if (on) { onlyOpenToday = false; openToday.classList.remove('on'); openToday.setAttribute('aria-pressed','false'); } }
    apply();
  }

  q.addEventListener('input', apply);
  day.addEventListener('change', () => { chipDay = null; chips.forEach(c => c.classList.remove('on')); apply(); });
  type.addEventListener('change', apply);
  openToday.addEventListener('click', () => toggle(openToday, 'open'));
  fullToday.addEventListener('click', () => toggle(fullToday, 'full'));
  chips.forEach(ch => ch.addEventListener('click', () => {
    const v = ch.dataset.day;
    const already = ch.classList.contains('on');
    chips.forEach(c => c.classList.remove('on'));
    day.value = '';
    if (already) { chipDay = null; } else { ch.classList.add('on'); chipDay = Number(v); }
    apply();
  }));
  document.getElementById('reset').addEventListener('click', () => {
    q.value = ''; day.value = ''; type.value = ''; chipDay = null;
    onlyOpenToday = false; onlyFullToday = false;
    openToday.classList.remove('on'); openToday.setAttribute('aria-pressed','false');
    fullToday.classList.remove('on'); fullToday.setAttribute('aria-pressed','false');
    chips.forEach(c => c.classList.remove('on')); apply();
  });
  computeLiveStatus();
  apply();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    build()
