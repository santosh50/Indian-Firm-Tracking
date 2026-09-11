import os
import logging
import pandas as pd
from tqdm import tqdm

from company_lookup import fetch_strikeoff_dates

logger = logging.getLogger(__name__)

INPUT_DIR = "data/"
OUTPUT_DIR = "outputs/"
INPUT_CIN_COLUMN = "CIN"
INPUT_STATUS_COLUMN = "CompanyStatus"
BATCH_SIZE = 1000

def get_output_csv_path(input_csv):
    state_name = os.path.splitext(os.path.basename(input_csv))[0]
    return os.path.join(OUTPUT_DIR, f"{state_name}_strikeoff.csv")

def has_pending_records(input_csv):
    output_csv = get_output_csv_path(input_csv)

    csv_to_check = output_csv if os.path.exists(output_csv) else input_csv
    if not os.path.exists(csv_to_check):
        logger.error(f"Input file not found: {input_csv}")
        return False

    df = pd.read_csv(csv_to_check)

    if "Date of Last AGM" not in df.columns:
        return (df[INPUT_STATUS_COLUMN] == "Strike Off").any()

    strikeoff_mask = df[INPUT_STATUS_COLUMN] == "Strike Off"
    pending_mask = strikeoff_mask & df["Date of Last AGM"].isna()
    return pending_mask.any()

def process_strikeoff_batch(page, context, input_csv, headless=False):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_csv = get_output_csv_path(input_csv)
    state_name = os.path.splitext(os.path.basename(input_csv))[0]

    if not os.path.exists(output_csv):
        if not os.path.exists(input_csv):
            logger.error(f"Input file not found: {input_csv}")
            return None
        logger.info(f"No existing output — creating working copy at {output_csv}")
        df = pd.read_csv(input_csv)
        df["Date of Last AGM"] = None
        df["Date of Balance Sheet"] = None
        df.to_csv(output_csv, index=False)

    df = pd.read_csv(output_csv)

    df["Date of Last AGM"] = df["Date of Last AGM"].astype("object")
    df["Date of Balance Sheet"] = df["Date of Balance Sheet"].astype("object")

    strikeoff_indices = df[df[INPUT_STATUS_COLUMN] == "Strike Off"].index
    pending_indices = [idx for idx in strikeoff_indices if pd.isna(df.at[idx, "Date of Last AGM"])]

    logger.info(
        f"{len(strikeoff_indices)} Strike Off record(s) total, "
        f"{len(strikeoff_indices) - len(pending_indices)} already done, "
        f"{len(pending_indices)} pending"
    )

    already_done = len(strikeoff_indices) - len(pending_indices)

    if len(pending_indices) > BATCH_SIZE:
        logger.info(f"Limiting this run to {BATCH_SIZE} of {len(pending_indices)} pending record(s)")
        pending_indices = pending_indices[:BATCH_SIZE]

    progress = tqdm(
        total=len(strikeoff_indices),
        initial=already_done,
        desc=f"{state_name} strike-off lookups",
        unit="company",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}{postfix}",
    )

    attempted = 0
    succeeded = 0

    for idx in pending_indices:
        cin = df.at[idx, INPUT_CIN_COLUMN]
        attempted += 1
        tqdm.write("-" * 70)
        progress.set_postfix_str(f"({succeeded}/{attempted} attempts succeeded)")

        dates = fetch_strikeoff_dates(page, context, cin, headless=headless)

        if dates:
            df.at[idx, "Date of Last AGM"] = dates.get("date_of_last_agm")
            df.at[idx, "Date of Balance Sheet"] = dates.get("date_of_balance_sheet")
            succeeded += 1
            progress.update(1)
        else:
            tqdm.write(f"Failed to fetch dates for CIN {cin}")
            logger.error(f"Failed to fetch dates for CIN {cin}")

        df.to_csv(output_csv, index=False)

    progress.close()
    logger.info(f"Saved results to {output_csv}")

    return df
