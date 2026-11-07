# LCSD Indoor Swimming Pools — Routine Day Off, Opening & Closing Dates

A plain-HTML reference for **every public swimming pool operated by the Hong Kong
Leisure and Cultural Services Department (LCSD / 康樂及文化事務署)** — 46 pools in total —
listing, for each pool:

| Field | What it means |
|---|---|
| **Routine day off** | The weekly cleansing day the pool closes (usually 10:00 a.m. to the end of the second session, rescheduled within the same week if it lands on a public holiday) |
| **Indoor pool closing date** | The date the indoor pool stops opening for its annual maintenance window |
| **Indoor pool opening date** | The date the indoor pool opens again (reopening) |
| **Indoor open period** | The complementary part of the year when the indoor pool is in service |
| **Outdoor pool closure** | Shown as context for complexes that have both indoor and outdoor pools |

**Live page:** <https://winglam01.github.io/lcsd-swimming-pools/>

### "Open today" filters

The page answers *can I swim today?* directly:

- **Open today** — every pool with at least one open session today, including pools whose
  daytime session is shut for the weekly cleansing but that reopen for the evening session.
- **Open all day today** — only pools with no closure of any kind today.

Pools inside their annual maintenance window are excluded from both. Each card carries a
badge saying which case applies: *Open today*, *Open evenings only today*, or
*Closed today · annual maintenance*. The same split is in the CSV's `Status today` column.

---

## Why two different "closures"

LCSD runs two separate calendars for every pool:

1. **Weekly cleansing (the routine "day off")** — one fixed weekday per pool.
   Every public pool is closed for roughly half a day each week while it is cleaned.
2. **Annual maintenance** — a multi-week or multi-month window per pool in which
   either the indoor pools, the outdoor pools, or the whole complex is taken out of
   service so that the plant can be serviced.

The two are independent: a pool can be on its cleansing day during a maintenance
window, and a complex with an outdoor pool usually keeps the indoor pool open
while the outdoor pool is being serviced (and vice versa). That is why the outdoor
closure is listed alongside the indoor dates.

## Common patterns

| Pattern | Pools |
|---|---|
| Whole complex closes 1 Nov – 31 Mar (indoor season is 1 Apr – 31 Oct) | most indoor-only complexes, e.g. Chai Wan, Kwai Shing, Tin Shui Wai, Sai Kung |
| Indoor pools close 16 Apr – 5 Jun, outdoor pools close 1 Nov – 15 Apr | Kowloon Park, Morse Park, Sha Tin (indoor part), Tuen Mun, Tin Sau Road, Sun Yat Sen Memorial Park |
| Indoor pools close 11 Sep – 31 Oct | Island East, Kennedy Town, Tai Kok Tsui, Ho Man Tin, Tung Cheong Street, Ping Shan Tin Shui Wai |
| Slightly different windows | Hammer Hill Road (indoor 11 May – 30 Jun), Shing Mun Valley (indoor 1 May – 30 Jun), Kwun Tong (indoor 2 Jan – 21 Feb), Wan Chai (1 Dec – 20 Jan), Siu Sai Wan (2 May – 26 Jul), Victoria Park (20 Feb – 21 Apr) |

The full per-pool breakdown is on the live page.

## Data files

- [`data/lcsd-indoor-pools.csv`](data/lcsd-indoor-pools.csv) — one row per pool, spreadsheet-friendly (UTF-8 with BOM).
- [`data/lcsd-indoor-pools.json`](data/lcsd-indoor-pools.json) — the same data as JSON, including
  the LCSD wording in both English and Chinese, phone/e-mail, and source URLs.

## Reproducing the data

The scripts in [`scripts/`](scripts/) scrape and rebuild everything from the official
LCSD pages. They are plain Python 3 with no third-party dependencies.

```bash
python scripts/parse_pools.py    # pool list + daily hours + closure day (TC & EN)
python scripts/fetch_lcsd.py     # download every per-pool detail page into data/pages/
python scripts/build_dataset.py  # merge, curate indoor windows, verify against source
python scripts/build_html.py     # render index.html
python scripts/export_csv.py     # write data/lcsd-indoor-pools.csv
```

`build_dataset.py` verifies every curated date string against the raw page text it was
taken from and prints any mismatch, so a silent typo cannot survive a rebuild.

## Source

All data comes from the Leisure and Cultural Services Department:

- [Public swimming pool information (EN)](https://www.lcsd.gov.hk/clpss/en/webApp/Swimming.do)
- [公眾游泳池資料 (中)](https://www.lcsd.gov.hk/clpss/tc/webApp/Swimming.do)
- [Facilities & Venues Search](https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do)
- [List of Facilities & Venues](https://www.lcsd.gov.hk/en/facilities/facilitieslist.html)

Data captured **6 November 2026**; LCSD detail pages were last revised **2026年11月6日**.

## Disclaimer

This is an unofficial convenience summary. Opening hours and closures change without
much notice — the LCSD page for each pool and the pool office (phone number on each
card) are authoritative. During the Lunar New Year (農曆年初一至初三) all public swimming
pools are closed.
