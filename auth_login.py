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

    logger.info("Waiting for OTP entry... (2 min timeout)")
    try:
        page.wait_for_url("**/application-history.html", timeout=120000)
    except Exception:
        logger.error("OTP step timed out — login not confirmed")
        return False

    context.storage_state(path=AUTH_FILE)
    logger.info("Login succeeded. Auth state saved")
    return True


def main():
    from playwright.sync_api import sync_playwright

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

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
        page.goto(MCA_LOGIN_URL, wait_until="domcontentloaded")

        if is_logged_in(page):
            logger.info("Already logged in — auth file is still valid, nothing to do.")
        elif login(page, context):
            logger.info(f"Login successful. {AUTH_FILE} created/updated.")
        else:
            logger.error("Login failed.")

        browser.close()


if __name__ == "__main__":
    main()
