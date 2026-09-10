import os
import logging
import pandas as pd

from company_lookup import fetch_strikeoff_dates

logger = logging.getLogger(__name__)

INPUT_DIR = "data/"
OUTPUT_DIR = "outputs/"
INPUT_CIN_COLUMN = "CIN"
INPUT_STATUS_COLUMN = "CompanyStatus"


def process_strikeoff_batch(page, input_csv):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    state_name = os.path.splitext(os.path.basename(input_csv))[0]
    output_csv = os.path.join(OUTPUT_DIR, f"{state_name}_strikeoff.csv")

    if not os.path.exists(output_csv):
        logger.info(f"No existing output — creating working copy at {output_csv}")
        df = pd.read_csv(input_csv)
        df["Date of Last AGM"] = None
        df["Date of Balance Sheet"] = None
        df.to_csv(output_csv, index=False)

    df = pd.read_csv(output_csv)

    strikeoff_indices = df[df[INPUT_STATUS_COLUMN] == "Strike Off"].index
    pending_indices = [idx for idx in strikeoff_indices if pd.isna(df.at[idx, "Date of Last AGM"])]

    logger.info(
        f"{len(strikeoff_indices)} Strike Off record(s) total, "
        f"{len(strikeoff_indices) - len(pending_indices)} already done, "
        f"{len(pending_indices)} pending"
    )

    for count, idx in enumerate(pending_indices, start=1):
        cin = df.at[idx, INPUT_CIN_COLUMN]
        logger.info(f"Processing {count}/{len(pending_indices)}: {cin}")

        dates = fetch_strikeoff_dates(page, cin)

        if dates:
            df.at[idx, "Date of Last AGM"] = dates.get("date_of_last_agm")
            df.at[idx, "Date of Balance Sheet"] = dates.get("date_of_balance_sheet")
        else:
            logger.error(f"Failed to fetch dates for CIN {cin}")

        df.to_csv(output_csv, index=False)

    logger.info(f"Saved results to {output_csv}")

    return df
