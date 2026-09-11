import os
import argparse
import logging
from tqdm import tqdm
from playwright.sync_api import sync_playwright

from auth_login import login, is_logged_in, AUTH_FILE
from strikeoff_batch import process_strikeoff_batch, has_pending_records, INPUT_DIR
from company_lookup import FatalReAuthError

MCA_COMPANY_LOOKUP_URL = "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"


class TqdmLoggingHandler(logging.Handler):
    """Routes log records through tqdm.write() so console output doesn't
    overlap the progress bar's line — tqdm clears the bar, prints the
    message on its own line, then redraws the bar underneath."""

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
    parser = argparse.ArgumentParser(description="Fetch strike-off dates for a state's companies")
    parser.add_argument("state", help="State name, matching <State_Name>.csv in the data folder")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (only safe if already logged in)")
    args = parser.parse_args()
    input_csv = os.path.join(INPUT_DIR, f"{args.state}.csv")

    if not has_pending_records(input_csv):
        logger.info(f"No pending records for {args.state} — nothing to do")
        return

    with sync_playwright() as p:
        logger.info("Launching Firefox browser")
        browser = p.firefox.launch(headless=args.headless)

        storage_state = AUTH_FILE if os.path.exists(AUTH_FILE) else None

        context = browser.new_context(
            storage_state=storage_state,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )
        page = context.new_page()

        logger.info("Opening MCA company lookup page")
        page.goto(MCA_COMPANY_LOOKUP_URL)
        page.wait_for_load_state("domcontentloaded")

        if is_logged_in(page):
            logger.info("[+] Already logged in.")
        else:
            logger.info("[-] Not logged in. Login required")
            logged_in = login(page, context)
            if not logged_in:
                logger.error("Login failed")
                return
            page.goto(MCA_COMPANY_LOOKUP_URL)

        try:
            process_strikeoff_batch(page, context, input_csv, headless=args.headless)
        except FatalReAuthError as e:
            logger.error(f"Stopping batch: {e}")

        browser.close()

if __name__ == "__main__":
    main()
