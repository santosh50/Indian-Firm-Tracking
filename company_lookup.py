import logging

from captcha_flow import solve_captcha_with_retries
from auth_login import login

logger = logging.getLogger(__name__)

MCA_COMPANY_LOOKUP_URL = "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"


class FatalReAuthError(Exception):
    """
    Raised when the session expires mid-batch and re-login fails while
    running headless — there's no visible window for OTP entry, so this
    can never succeed on its own. Meant to propagate all the way up and
    stop the batch, rather than be treated as a per-CIN failure that
    just gets retried (which would otherwise silently repeat forever).
    """
    pass


def _extract_labeled_value(page, cell_id):
    try:
        value = page.locator(f"#{cell_id}").inner_text(timeout=3000).strip()
    except Exception:
        logger.debug(f"{cell_id} not found on page — treating as Not Available")
        return "Not Available"

    if value in ("-", ""):
        value = "Not Available"

    return value

def _dismiss_lingering_modal(page):
    modal = page.locator("#captchaModal")
    if modal.count() == 0 or not modal.first.is_visible():
        return

    logger.warning("Lingering captcha modal detected — reloading page")
    page.reload(wait_until="domcontentloaded")

def _ensure_on_lookup_page(page, context, headless=False):
    if "MDS.html" in page.url:
        return True

    logger.info("Navigating to company lookup page")
    page.goto(MCA_COMPANY_LOOKUP_URL, wait_until="domcontentloaded")

    if "MDS.html" in page.url:
        return True

    logger.warning("Session expired mid-batch — redirected away from lookup page. Re-authenticating")
    if not login(page, context):
        if headless:
            raise FatalReAuthError(
                "Re-authentication failed while running headless — OTP entry "
                "requires a visible window. Rerun without --headless to log in manually."
            )
        logger.error("Re-authentication failed")
        return False

    page.goto(MCA_COMPANY_LOOKUP_URL, wait_until="domcontentloaded")

    if "MDS.html" not in page.url:
        logger.error("Still not on lookup page after re-authentication")
        return False

    return True

def fetch_strikeoff_dates(page, context, cin, headless=False):
    if not _ensure_on_lookup_page(page, context, headless=headless):
        return None

    _dismiss_lingering_modal(page)

    logger.info(f"Fetching strike-off dates for CIN: {cin}")

    try:
        cin_input = page.get_by_placeholder("Enter Company/LLP name")
        cin_input.click()
        cin_input.fill(cin)
        page.wait_for_timeout(300)
        page.locator("#searchicon").click()
    except Exception as e:
        logger.error(f"Could not enter CIN {cin}: {e}")
        return None

    logger.info("Solving captcha")
    if not solve_captcha_with_retries(page, "Submit"):
        logger.error(f"Could not solve first captcha for CIN {cin}")
        return None

    try:
        page.get_by_text(cin, exact=True).first.click(timeout=15000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
        page.screenshot(path=f"debug_fail_cinlink_{cin}.png", full_page=True)
        logger.error(f"Could not click CIN link for {cin}: {e}")
        return None

    captcha_locator = page.locator("text=Enter Captcha")

    if captcha_locator.count() > 0 and captcha_locator.first.is_visible():
        logger.info("Second captcha detected — solving")
        if not solve_captcha_with_retries(page, submit_button_text="Submit"):
            logger.error(f"Could not solve second captcha for CIN {cin}")
            return None
    else:
        logger.info("No second captcha — proceeding directly")

    page.wait_for_load_state("networkidle")

    try:
        page.wait_for_url("**/company-master-info.html", timeout=15000)
    except Exception as e:
        page.screenshot(path=f"debug_fail_masterinfo_{cin}.png", full_page=True)
        logger.error(f"Master data detail page did not load for CIN {cin}: {e}")
        return None

    page.wait_for_load_state("networkidle")

    dates = {
        "date_of_last_agm": _extract_labeled_value(page, "dateOfLastAGM"),
        "date_of_balance_sheet": _extract_labeled_value(page, "DateofBalanceSheet"),
    }
    logger.info(f"Extracted dates for CIN {cin}: {dates}")
    return dates

if __name__ == '__main__':
    import os
    from playwright.sync_api import sync_playwright

    TEST_CIN = "U52609AR2017PTC013503"
    AUTH_FILE = "auth_state.json"

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)

        storage_state = AUTH_FILE if os.path.exists(AUTH_FILE) else None
        context = browser.new_context(storage_state=storage_state)
        page = context.new_page()

        print("Opening MCA company lookup page")
        page.goto(MCA_COMPANY_LOOKUP_URL)
        page.wait_for_load_state("domcontentloaded")

        result = fetch_strikeoff_dates(page, context, TEST_CIN)
        print(f"\nResult for {TEST_CIN}: {result}")

        input("Press Enter to close browser...")
        browser.close()
