import os
import logging
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from captcha_flow import solve_captcha_with_retries
from company_lookup import fetch_strikeoff_dates

TEST_CIN = "U74999GJ1995PTC025739"
AUTH_FILE = "auth_state.json"
MCA_LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"
MCA_COMPANY_LOOKUP_URL = "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log", mode="w"),
    ],
)

logger = logging.getLogger(__name__)

def is_logged_in(page) -> bool:
    try:
        page.locator("button", has_text="Hello").first.wait_for(state="visible", timeout=3000)
        return True
    except Exception:
        return False

def login(page, context):
    logger.info("Opening MCA login page")
    page.goto(MCA_LOGIN_URL, wait_until="domcontentloaded")

    load_dotenv()
    user_id = os.environ.get("MCA_USER_ID", "")
    password = os.environ.get("MCA_PASSWORD", "")

    logger.info("Filling in User ID and Password")
    try:
        user_input = page.locator("input[type='text']:visible").nth(1)
        pass_input = page.locator("input[type='password']:visible").first
        
        user_input.click()
        user_input.fill(user_id)

        pass_input.click()
        pass_input.fill(password)

        page.get_by_text("Login", exact=True).first.click(timeout=5000)
    except Exception as e:
        logger.error(f"[!] Could not fill credentials: {e}")
        return

    if not solve_captcha_with_retries(page, submit_button_text="Continue"):
        return False

    logger.info("Waiting for OTP entry...")
    try:
        page.wait_for_url("**/application-history.html", timeout=120000)
    except Exception:
        logger.error("OTP step timed out — login not confirmed")
        return False

    context.storage_state(path=AUTH_FILE)
    logger.info("Login succeeded. Auth state saved")
    return True
    

def main():
    with sync_playwright() as p:
        logger.info("Launching Firefox browser")
        browser = p.firefox.launch(headless=False)

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

        fetch_strikeoff_dates(page, TEST_CIN)

        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    main()
