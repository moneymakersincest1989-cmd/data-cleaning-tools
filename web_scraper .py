"""
web_scraper.py — Reusable table/list scraper

Pulls structured data from a webpage into a CSV, ready to hand off
to data_cleaner.py.

Two modes:
  1. TABLE mode  — grabs <table> elements from a page (default)
  2. LIST mode   — grabs repeating items by CSS selector

USAGE:
    # Grab all tables from a page (saves table_1.csv, table_2.csv, ...)
    python3 web_scraper.py "https://example.com/page" --tables

    # Grab repeating items by CSS selector into one CSV
    python3 web_scraper.py "https://example.com/products" \
        --selector ".product" \
        --fields "name:.title,price:.price,link:a@href" \
        --out products.csv

FIELD SYNTAX (for --fields):
    label:.css_selector          -> text inside the matched element
    label:.css_selector@attr     -> value of an attribute (e.g. a@href, img@src)

RESPECTFUL SCRAPING:
    - Sends a normal browser User-Agent
    - Waits 1 second between requests
    - Always check a site's Terms of Service and robots.txt before scraping.
      Scrape public data only. Never scrape behind logins or personal data.
"""
import sys
import csv
import time
import argparse

import requests
from bs4 import BeautifulSoup
import pandas as pd


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def fetch(url):
    """Download a page politely, raise a clear error if it fails."""
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    time.sleep(1)  # be polite between requests
    return resp.text


def scrape_tables(url):
    """Extract every <table> on the page into a list of DataFrames."""
    from io import StringIO
    html = fetch(url)
    tables = pd.read_html(StringIO(html))  # pandas parses all tables for you
    if not tables:
        print("No <table> elements found on that page.")
        return []
    for i, df in enumerate(tables, 1):
        out = f"table_{i}.csv"
        df.to_csv(out, index=False)
        print(f"✓ Saved {out}  ({len(df)} rows, {len(df.columns)} columns)")
    return tables


def parse_field_spec(spec):
    """Turn 'name:.title,price:.price,link:a@href' into a list of rules."""
    rules = []
    for part in spec.split(","):
        label, selector = part.split(":", 1)
        attr = None
        if "@" in selector:
            selector, attr = selector.rsplit("@", 1)
        rules.append((label.strip(), selector.strip(), attr))
    return rules


def scrape_list(url, item_selector, field_spec, out_path):
    """Extract repeating items (cards, rows, listings) by CSS selector."""
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    rules = parse_field_spec(field_spec)

    items = soup.select(item_selector)
    if not items:
        print(f"No elements matched selector: {item_selector}")
        return

    rows = []
    for item in items:
        row = {}
        for label, selector, attr in rules:
            found = item.select_one(selector) if selector else item
            if found is None:
                row[label] = None
            elif attr:
                row[label] = found.get(attr)
            else:
                row[label] = found.get_text(strip=True)
        rows.append(row)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[r[0] for r in rules])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Saved {out_path}  ({len(rows)} items)")


def main():
    p = argparse.ArgumentParser(description="Scrape a webpage into CSV.")
    p.add_argument("url", help="Page URL to scrape")
    p.add_argument("--tables", action="store_true", help="Grab all <table> elements")
    p.add_argument("--selector", help="CSS selector for repeating items (list mode)")
    p.add_argument("--fields", help="Field spec: 'label:.sel,label2:.sel@attr'")
    p.add_argument("--out", default="scraped.csv", help="Output CSV path (list mode)")
    args = p.parse_args()

    try:
        if args.tables:
            scrape_tables(args.url)
        elif args.selector and args.fields:
            scrape_list(args.url, args.selector, args.fields, args.out)
        else:
            print("Choose a mode: --tables  OR  --selector + --fields")
            print('Example: python3 web_scraper.py "URL" --tables')
            sys.exit(1)
    except requests.HTTPError as e:
        print(f"Could not fetch the page: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
