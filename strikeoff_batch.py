import os
import glob
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

def process_strikeoff_batch(page, context, input_csv):
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
    )

    attempted = 0
    succeeded = 0

    for idx in pending_indices:
        cin = df.at[idx, INPUT_CIN_COLUMN]
        attempted += 1
        progress.set_postfix_str(f"{cin} ({succeeded}/{attempted} attempts succeeded)")
        logger.debug(f"Processing: {cin}")

        dates = fetch_strikeoff_dates(page, context, cin)

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

def process_all_states(page, context, input_dir=INPUT_DIR, output_dir=OUTPUT_DIR):
    csv_files = sorted(glob.glob(os.path.join(input_dir, "*.csv")))
    logger.info(f"Found {len(csv_files)} state CSV file(s) to process")

    results = {}
    for csv_path in csv_files:
        state_name = os.path.splitext(os.path.basename(csv_path))[0]

        logger.info(f"--- Processing state: {state_name} ---")
        try:
            results[state_name] = process_strikeoff_batch(page, context, csv_path)
        except Exception as e:
            logger.error(f"Failed to process {state_name}: {e}")
            results[state_name] = None

    return results
