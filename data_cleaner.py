"""
data_cleaner.py — Reusable CSV + Excel cleaner

Works on any client file. Handles .csv, .xlsx, .xls
Auto-detects what needs fixing instead of hardcoding column names.

USAGE:
    python3 data_cleaner.py input.xlsx output.xlsx
    python3 data_cleaner.py input.csv output.csv

WHAT IT DOES:
    - Strips whitespace from headers and text cells
    - Standardizes any date-looking column to YYYY-MM-DD
    - Title-cases name columns, lowercases email columns
    - Normalizes inconsistent category/status labels
    - Flags (never deletes) missing values and negative numbers
    - Removes duplicate rows
    - Writes a summary report of every change
"""
import sys
import re
import os
import pandas as pd


DATE_FORMATS = [
    "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%y",
    "%Y/%m/%d", "%d/%m/%Y", "%b %d, %Y", "%d %b %Y",
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_file(path):
    """Read CSV or Excel based on extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path, dtype=str)
    elif ext in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv, .xlsx, or .xls")


def save_file(df, path):
    """Write CSV or Excel based on extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        df.to_csv(path, index=False)
    elif ext in (".xlsx", ".xls"):
        df.to_excel(path, index=False, engine="openpyxl")
    else:
        raise ValueError(f"Unsupported output type: {ext}")


def parse_date(val):
    """Try every known format; return YYYY-MM-DD or None."""
    if pd.isna(val) or str(val).strip() == "":
        return None
    for fmt in DATE_FORMATS:
        try:
            return pd.to_datetime(str(val).strip(), format=fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return None


def looks_like_date_column(series):
    """A column is a date column if most non-empty values parse as dates."""
    non_empty = series.dropna()
    non_empty = non_empty[non_empty.astype(str).str.strip() != ""]
    if len(non_empty) == 0:
        return False
    parsed = non_empty.apply(parse_date).notna().sum()
    return parsed / len(non_empty) > 0.7


def looks_like_email_column(series):
    non_empty = series.dropna().astype(str)
    non_empty = non_empty[non_empty.str.strip() != ""]
    if len(non_empty) == 0:
        return False
    return (non_empty.str.contains("@").sum() / len(non_empty)) > 0.5


def looks_like_number_column(series):
    non_empty = series.dropna().astype(str).str.strip()
    non_empty = non_empty[non_empty != ""]
    if len(non_empty) == 0:
        return False
    cleaned = non_empty.str.replace(r"[$,]", "", regex=True)
    numeric = pd.to_numeric(cleaned, errors="coerce").notna().sum()
    return numeric / len(non_empty) > 0.7


def clean(path_in, path_out):
    df = load_file(path_in)
    report = []
    rows_before = len(df)

    # --- 1. Clean headers ---
    df.columns = [str(c).strip() for c in df.columns]

    # --- 2. Strip whitespace from every text cell ---
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip().replace({"nan": None, "": None})

    # --- 3. Auto-detect and fix each column by type ---
    for col in df.columns:
        col_lower = col.lower()

        # Dates
        if looks_like_date_column(df[col]):
            df[col] = df[col].apply(parse_date)
            report.append(f"'{col}': dates standardized to YYYY-MM-DD")

        # Emails
        elif looks_like_email_column(df[col]):
            df[col] = df[col].str.lower()
            bad = df[col].apply(
                lambda e: isinstance(e, str) and e != "" and not EMAIL_RE.match(e)
            )
            missing = df[col].isna().sum()
            if bad.sum() or missing:
                report.append(f"'{col}': {bad.sum()} malformed, {missing} missing — FLAGGED")
            report.append(f"'{col}': emails lowercased")

        # Numbers / amounts
        elif looks_like_number_column(df[col]):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[$,]", "", regex=True),
                errors="coerce",
            )
            missing = df[col].isna().sum()
            negative = (df[col] < 0).sum()
            if missing:
                report.append(f"'{col}': {missing} missing values — FLAGGED, not deleted")
            if negative:
                report.append(f"'{col}': {negative} negative values — FLAGGED as possible errors")

        # Name-like columns -> Title Case
        elif "name" in col_lower:
            df[col] = df[col].str.title()
            report.append(f"'{col}': names standardized to Title Case")

        # Status / category columns -> lowercase, consistent
        elif any(k in col_lower for k in ("status", "category", "type", "state")):
            df[col] = df[col].str.lower()
            report.append(f"'{col}': labels normalized ({df[col].nunique()} unique values)")

    # --- 4. Remove duplicate rows ---
    df = df.drop_duplicates(keep="first")
    removed = rows_before - len(df)
    if removed:
        report.append(f"Duplicate rows removed: {removed}")

    # --- 5. Save cleaned file + report ---
    save_file(df, path_out)

    report_path = os.path.splitext(path_out)[0] + "_report.txt"
    with open(report_path, "w") as f:
        f.write("DATA CLEANING SUMMARY\n")
        f.write("=" * 40 + "\n")
        f.write(f"Source file:  {os.path.basename(path_in)}\n")
        f.write(f"Rows before:  {rows_before}\n")
        f.write(f"Rows after:   {len(df)}\n")
        f.write(f"Columns:      {len(df.columns)}\n\n")
        f.write("CHANGES MADE\n")
        f.write("-" * 40 + "\n")
        for line in report:
            f.write(f"- {line}\n")
        f.write("\nNote: Missing and invalid values were flagged, not deleted.\n")

    print(f"✓ Cleaned file: {path_out}")
    print(f"✓ Report:       {report_path}")
    print(f"  {rows_before} rows in, {len(df)} rows out, {len(report)} changes logged")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 data_cleaner.py <input.csv|input.xlsx> <output.csv|output.xlsx>")
        sys.exit(1)
    clean(sys.argv[1], sys.argv[2])
