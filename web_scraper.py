import os
import sys
import argparse
import logging
from playwright.sync_api import sync_playwright
from tqdm import tqdm

from auth_login import is_logged_in, AUTH_FILE
from strikeoff_batch import process_strikeoff_batch, has_pending_records, INPUT_DIR
from company_lookup import FatalReAuthError, MCA_COMPANY_LOOKUP_URL


class TqdmLoggingHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
        except Exception:
            self.handleError(record)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        TqdmLoggingHandler(),
        logging.FileHandler("scraper.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch strike-off dates for a state's companies, using "
                     "an existing auth file. Exits with an error if the "
                     "auth file is missing or the session has expired."
    )
    parser.add_argument("state", help="State name, matching <State_Name>.csv in the data folder")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    args = parser.parse_args()
    input_csv = os.path.join(INPUT_DIR, f"{args.state}.csv")

    if not os.path.exists(AUTH_FILE):
        logger.error(f"Auth file not found: {AUTH_FILE}. Log in manually first to create it.")
        sys.exit(1)

    if not has_pending_records(input_csv):
        logger.info(f"No pending records for {args.state} — nothing to do")
        return

    with sync_playwright() as p:
        logger.info(f"Launching Firefox browser (headless={args.headless})")
        browser = p.firefox.launch(headless=args.headless)

        context = browser.new_context(
            storage_state=AUTH_FILE,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )
        page = context.new_page()

        logger.info("Opening MCA company lookup page")
        page.goto(MCA_COMPANY_LOOKUP_URL)
        page.wait_for_load_state("domcontentloaded")

        if not is_logged_in(page):
            logger.error(
                "Auth file present but session is invalid or expired. "
                "Log in manually to refresh the auth file, then rerun this script."
            )
            browser.close()
            sys.exit(1)

        logger.info("[+] Session valid — already logged in.")

        try:
            process_strikeoff_batch(page, context, input_csv)
        except FatalReAuthError as e:
            logger.error(f"Stopping batch: {e}")
            browser.close()
            sys.exit(1)

        browser.close()

if __name__ == "__main__":
    main()
