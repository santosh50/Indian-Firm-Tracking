"""
Fix Pincode column for all 2020+ project rows in blr_projects_software_and_commercial_v1.xlsx,
using the RoC Karnataka master data as the source of truth.

WHAT THIS DOES:
- Loads your project Excel file and the RoC Karnataka master data CSV.
- For each unique company (by Company Code) in rows from 2020 onward,
  finds the best-matching company in the RoC data (exact match on
  normalized name first, then fuzzy match as a fallback).
- Extracts the pincode from that company's registered office address.
- For 2020+ rows: overwrites Pincode with the matched value ONLY when the
  match is trustworthy (EXACT MATCH or FUZZY MATCH, score >= threshold).
  If no reliable match is found (LOW CONFIDENCE or NOT FOUND), the
  Pincode is left BLANK rather than keeping the original (known
  incorrect) value.
- Rows before 2020 are left completely untouched. Latitude/Longitude
  are never touched either way.
- Adds match_status and match_score columns so you can see exactly why
  a pincode was filled in, left blank, or (for pre-2020 rows) skipped.

KNOWN LIMITATION (not a bug):
This only checks the Karnataka RoC file. Companies actually registered
in a different state (head office in Mumbai, Delhi, etc., with just a
project site in Bangalore) will not be found here and will end up with
a blank pincode -- that's expected, not an error.

SETUP:
    pip install pandas rapidfuzz openpyxl --break-system-packages

USAGE:
    Edit the file paths below, then run:
        python3 fix_pincodes_2020.py
"""

import re
import pandas as pd
from rapidfuzz import fuzz

# --- EDIT THESE PATHS ---
PROJECTS_FILE = "blr_projects_software_and_commercial_v1.xlsx"
ROC_MASTER_DATA_FILE = "roc_company_master_data.csv"  # Karnataka RoC master data
OUTPUT_FILE = "blr_projects_2020_plus_with_pincode.xlsx"

YEAR_CUTOFF = 2020
FUZZY_MATCH_THRESHOLD = 85  # below this -> treated as no reliable match (pincode left blank)


def normalize_name(name) -> str:
    """
    Normalize a company name for matching: uppercase, strip punctuation
    and bracketed annotations (e.g. '[merged]'), collapse spaced-out
    single-letter acronyms ('A B B' -> 'ABB'), and unify common suffix
    variants (Pvt Ltd / Private Limited / '&' -> 'AND').
    """
    if pd.isna(name):
        return ""
    name = str(name).upper()
    name = re.sub(r"\[.*?\]", "", name)
    name = name.replace(".", "").replace(",", "")

    tokens = name.split()
    collapsed = []
    i = 0
    while i < len(tokens):
        if len(tokens[i]) == 1 and tokens[i].isalpha():
            run = tokens[i]
            j = i + 1
            while j < len(tokens) and len(tokens[j]) == 1 and tokens[j].isalpha():
                run += tokens[j]
                j += 1
            collapsed.append(run)
            i = j
        else:
            collapsed.append(tokens[i])
            i += 1
    name = " ".join(collapsed)

    replacements = {
        "PVT LTD": "PRIVATE LIMITED",
        "PRIVATE LTD": "PRIVATE LIMITED",
        "PVT": "PRIVATE",
        "LTD": "LIMITED",
        "&": "AND",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return " ".join(name.split())


def extract_pincode(address) -> str:
    """
    Pull a 6-digit Indian pincode out of a free-text address string.
    Treats '000000' as missing/invalid, since it appears as a placeholder
    in some RoC records rather than a real pincode.
    """
    if pd.isna(address):
        return ""
    match = re.search(r"\b(\d{6})\b", str(address))
    if not match:
        return ""
    pincode = match.group(1)
    return "" if pincode == "000000" else pincode


def main():
    projects_df = pd.read_excel(PROJECTS_FILE)
    roc_df = pd.read_csv(ROC_MASTER_DATA_FILE, low_memory=False)

    roc_df["_norm"] = roc_df["CompanyName"].apply(normalize_name)
    roc_df["_pincode"] = roc_df["Registered_Office_Address"].apply(extract_pincode)

    # Exact-match index: normalized name -> row index (first occurrence)
    exact_index = {}
    for idx, n in enumerate(roc_df["_norm"]):
        if n not in exact_index:
            exact_index[n] = idx

    # Blocking index for fuzzy fallback: first token -> list of row indices.
    # This avoids comparing every company against all 258k+ RoC rows.
    block_index = {}
    for idx, n in enumerate(roc_df["_norm"]):
        tok = n.split()[0] if n else ""
        block_index.setdefault(tok, []).append(idx)

    is_2020_plus = projects_df["Year"] >= YEAR_CUTOFF
    subset = projects_df[is_2020_plus].copy()  # work on a copy -- original file is never written to
    unique_companies = subset[["Company Code", "Company"]].drop_duplicates(subset=["Company Code"])

    print(f"Total rows in original file: {len(projects_df)}")
    print(f"Rows {YEAR_CUTOFF}+: {len(subset)}")
    print(f"Unique companies to match: {len(unique_companies)}")

    lookup = {}  # company code -> (matched_name, score, pincode, status)

    for _, row in unique_companies.iterrows():
        code = row["Company Code"]
        name = row["Company"]
        norm = normalize_name(name)

        if not norm:
            lookup[code] = ("", 0, "", "NOT FOUND")
            continue

        # 1. Try exact match first
        if norm in exact_index:
            idx = exact_index[norm]
            lookup[code] = (roc_df.iloc[idx]["CompanyName"], 100, roc_df.iloc[idx]["_pincode"], "EXACT MATCH")
            continue

        # 2. Fuzzy fallback, restricted to candidates sharing the first token
        tok = norm.split()[0]
        candidates = block_index.get(tok, [])
        if not candidates:
            # broaden slightly: any RoC name containing the token anywhere
            candidates = [i for i, n in enumerate(roc_df["_norm"]) if tok in n]

        if not candidates:
            lookup[code] = ("", 0, "", "NOT FOUND")
            continue

        best_score = -1
        best_idx = None
        for idx in candidates:
            score = fuzz.token_sort_ratio(norm, roc_df.iloc[idx]["_norm"])
            if score > best_score:
                best_score = score
                best_idx = idx

        status = "FUZZY MATCH" if best_score >= FUZZY_MATCH_THRESHOLD else "LOW CONFIDENCE"
        lookup[code] = (
            roc_df.iloc[best_idx]["CompanyName"],
            best_score,
            roc_df.iloc[best_idx]["_pincode"],
            status,
        )

    def get_field(code, field_idx):
        return lookup.get(code, ("", 0, "", "NOT FOUND"))[field_idx]

    subset["matched_roc_company_name"] = subset["Company Code"].map(lambda c: get_field(c, 0))
    subset["match_score"] = subset["Company Code"].map(lambda c: get_field(c, 1))
    subset["match_status"] = subset["Company Code"].map(lambda c: get_field(c, 3))

    # The original Pincode column is numeric (float), but matched pincodes
    # come out as strings (to preserve any leading zeros). Convert to a
    # consistent string type before writing values in.
    subset["Pincode"] = subset["Pincode"].apply(
        lambda x: "" if pd.isna(x) else str(int(x)) if isinstance(x, float) else str(x)
    )

    # Use the matched pincode ONLY for trustworthy matches (EXACT MATCH or
    # FUZZY MATCH, score >= FUZZY_MATCH_THRESHOLD). For LOW CONFIDENCE or
    # NOT FOUND, BLANK the pincode out entirely -- the original values are
    # known to be wrong, so keeping them would be actively misleading. A
    # blank clearly signals "needs manual lookup."
    new_pincodes = subset["Company Code"].map(lambda c: get_field(c, 2))
    match_statuses = subset["match_status"]
    trustworthy = match_statuses.isin(["EXACT MATCH", "FUZZY MATCH"]) & (new_pincodes != "")

    subset.loc[trustworthy, "Pincode"] = new_pincodes[trustworthy]
    subset.loc[~trustworthy, "Pincode"] = ""

    # Save ONLY the 2020+ subset with corrected pincodes. The original
    # input file (PROJECTS_FILE) is never modified or re-saved.
    subset.to_excel(OUTPUT_FILE, index=False)

    status_counts = pd.Series([lookup[c][3] for c in unique_companies["Company Code"]]).value_counts()
    print("\nMatch status breakdown (unique companies):")
    print(status_counts)
    print(f"\nSaved {YEAR_CUTOFF}+ rows with corrected pincodes to {OUTPUT_FILE}")
    print("Original input file was not modified.")
    print("Review rows with match_status = 'LOW CONFIDENCE' or 'NOT FOUND' -- their Pincode is blank.")


if __name__ == "__main__":
    main()
