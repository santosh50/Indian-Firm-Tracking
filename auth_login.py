import os
import logging
from dotenv import load_dotenv

from captcha_flow import solve_captcha_with_retries

logger = logging.getLogger(__name__)

AUTH_FILE = "auth_state.json"
MCA_LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"


def is_logged_in(page, timeout=4000) -> bool:
    try:
        page.locator("button", has_text="Hello").first.wait_for(state="visible", timeout=timeout)
        return True
    except Exception:
        return False


def login(page, context):
    if "fologin.html" not in page.url:
        logger.info("Not on login page — navigating there directly")
        page.goto(MCA_LOGIN_URL, wait_until="domcontentloaded")
    else:
        logger.info("Site redirected to login page")

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
        return False

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
