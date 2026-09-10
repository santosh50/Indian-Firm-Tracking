import sys
import os
import pandas as pd

INPUT_STATUS_COLUMN = "CompanyStatus"

def filter_to_strikeoff_only(input_csv, output_csv=None):
    df = pd.read_csv(input_csv)

    strikeoff_df = df[df[INPUT_STATUS_COLUMN] == "Strike Off"]

    if output_csv is None:
        base, ext = os.path.splitext(input_csv)
        output_csv = f"{base}_only{ext}"

    strikeoff_df.to_csv(output_csv, index=False)
    print(f"Saved {len(strikeoff_df)} Strike Off record(s) to {output_csv}")
    return strikeoff_df

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python filter_strikeoff.py <input_csv> [output_csv]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    filter_to_strikeoff_only(input_path, output_path)
