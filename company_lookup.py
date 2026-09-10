import logging

from captcha_flow import solve_captcha_with_retries

logger = logging.getLogger(__name__)

def _extract_labeled_value(page, cell_id):
    return page.locator(f"#{cell_id}").inner_text().strip()

def fetch_strikeoff_dates(page, cin):
    logger.info(f"Fetching strike-off dates for CIN: {cin}")

    try:
        cin_input = page.get_by_placeholder("Enter Company/LLP name")
        cin_input.click()
        cin_input.fill(cin)
        page.wait_for_timeout(300)
        cin_input.press("Enter")
    except Exception as e:
        logger.error(f"Could not enter CIN {cin}: {e}")
        return None

    logger.info("Solving captcha")
    if not solve_captcha_with_retries(page, "Submit"):
        logger.error(f"Could not solve first captcha for CIN {cin}")
        return None

    try:
        page.get_by_text(cin, exact=True).first.click(timeout=5000)
        page.wait_for_load_state("networkidle")
    except Exception as e:
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

    dates = {
        "date_of_last_agm": _extract_labeled_value(page, "dateOfLastAGM"),
        "date_of_balance_sheet": _extract_labeled_value(page, "DateofBalanceSheet"),
    }
    logger.info(f"Extracted dates for CIN {cin}")
    return dates

if __name__ == '__main__':
    # Quick manual test for a single CIN: reuses the saved login session (auth_state.json)
    import os
    from playwright.sync_api import sync_playwright
 
    TEST_CIN = "U74999GJ1995PTC025739"
    AUTH_FILE = "auth_state.json"
    MCA_COMPANY_LOOKUP_URL = "https://www.mca.gov.in/content/mca/global/en/mca/master-data/MDS.html"

 
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        if not os.path.exists(AUTH_FILE):
            logger.info("Auth file missing")
        
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        print("Opening MCA company lookup page")
        page.goto(MCA_COMPANY_LOOKUP_URL)
        page.wait_for_load_state("domcontentloaded")
 
        result = fetch_strikeoff_dates(page, TEST_CIN)
        print(f"\nResult for {TEST_CIN}: {result}")

        input("Press Enter to close browser...")
        browser.close()
