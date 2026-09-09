import logging

from captcha_flow import solve_captcha_with_retries

logger = logging.getLogger(__name__)

def fetch_strikeoff_dates(page, cin):
    logger.info(f"Fetching strike-off dates for CIN: {cin}")

    try:
        cin_input = page.get_by_placeholder("Enter Company/LLP name")
        cin_input.click()
        cin_input.fill(cin)
        cin_input.press("Enter")
    except Exception as e:
        logger.error(f"Could not enter CIN {cin}: {e}")
        return None

    if not solve_captcha_with_retries(page, "Submit"):
        logger.error(f"Could not solve captcha for CIN {cin}")
        return None

    # page.wait_for_load_state("networkidle")

    # # TODO: replace with real selector(s) once we know the result layout
    # strikeoff_dates = None

    # return strikeoff_dates
