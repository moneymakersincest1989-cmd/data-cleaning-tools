# Data Cleaning & Scraping Tools

Python tools for cleaning messy spreadsheets and extracting structured data from web pages.

Built and used for freelance data work. Every job returns a **clean file plus a report documenting exactly what changed** — suspect values are flagged, never silently deleted.

---

## What's here

| Tool | What it does |
|---|---|
| `data_cleaner.py` | Cleans CSV and Excel files. Auto-detects column types — no config needed. |
| `web_scraper.py` | Pulls tables or repeating list items off a web page into CSV. |

The two chain together: scrape a page, then clean the output.

---

## data_cleaner.py

Point it at any CSV or Excel file. It figures out the structure itself.

```bash
python3 data_cleaner.py input.xlsx output.xlsx
```

**What it handles:**

- **Dates** — parses 8+ input formats (`03/14/2026`, `2026-03-15`, `14-03-2026`, `3/17/26`, …) and standardizes everything to `YYYY-MM-DD`
- **Emails** — lowercases, validates format, flags malformed and missing addresses
- **Numbers** — strips `$` and `,`, converts to numeric, flags missing values and negatives that look like data-entry errors
- **Names** — normalizes to Title Case, strips stray whitespace
- **Status/category columns** — collapses `Completed` / `completed` / `COMPLETED` into one consistent value
- **Duplicates** — removes exact duplicate rows
- **Headers** — trims whitespace from column names

**Column detection is automatic.** It samples the values in each column and decides what it is — so it works on a file whose headers are `Signup Date` and `Contact Email` just as well as one with `date` and `email`. No editing the script per client.

**Nothing is deleted silently.** Missing and invalid values are flagged in the report so the client can see what was wrong with the original data.

### Sample output

Running it on `samples/messy_sales_data.csv`:

```
DATA CLEANING SUMMARY
========================================
Source file:  client_records.xlsx
Rows before:  8
Rows after:   7
Columns:      6

CHANGES MADE
----------------------------------------
- 'Full Name': names standardized to Title Case
- 'Contact Email': 1 malformed, 1 missing — FLAGGED
- 'Contact Email': emails lowercased
- 'Signup Date': dates standardized to YYYY-MM-DD
- 'Revenue': 1 missing values — FLAGGED, not deleted
- 'Revenue': 1 negative values — FLAGGED as possible errors
- 'Account Type': labels normalized (2 unique values)
- Duplicate rows removed: 1

Note: Missing and invalid values were flagged, not deleted.
```

See `samples/` for the full before/after files.

---

## web_scraper.py

Two modes.

**Tables** — grab every `<table>` on a page:

```bash
python3 web_scraper.py "https://example.com/stats" --tables
```

Saves `table_1.csv`, `table_2.csv`, … one per table found.

**Lists** — grab repeating items (product cards, directory entries) by CSS selector:

```bash
python3 web_scraper.py "https://example.com/products" \
  --selector ".product" \
  --fields "name:.title,price:.price,link:a@href" \
  --out products.csv
```

Field syntax:
- `label:.css_selector` → the text inside the matched element
- `label:.css_selector@attr` → an attribute value (`a@href`, `img@src`)

**Built to be polite:** sends a normal browser User-Agent, waits 1 second between requests. Intended for public data only — not for content behind logins, and not for scraping personal information.

---

## Chaining them

```bash
python3 web_scraper.py "https://example.com/listings" --tables
python3 data_cleaner.py table_2.csv table_2_clean.csv
```

Raw page → clean spreadsheet → change report.

---

## Setup

```bash
pip3 install pandas openpyxl requests beautifulsoup4 lxml
```

Python 3.9+.

---

## Notes

These are working tools, not a demo. They're written to be pointed at unfamiliar client files without modification — which is why column detection is inferred from the data rather than hardcoded to specific header names.
