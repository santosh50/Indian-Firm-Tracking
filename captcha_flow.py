import logging
from PIL import Image

from captcha_solver import solve_captcha

IMG_PATH = "captcha.png"
MAX_CAPTCHA_REFRESHES = 10

logger = logging.getLogger(__name__)

def fetch_captcha_image(page):
    img_selector = "img[src*='captcha']"
    spinner_selector = "[role='status']"

    logger.info("Fetching captcha image")
    captcha_element = page.wait_for_selector(
        img_selector,
        state="visible",
    )

    try:
        page.wait_for_selector(spinner_selector, state="visible", timeout=2000)
        page.wait_for_selector(spinner_selector, state="hidden", timeout=10000)
    except Exception:
        pass

    captcha_element.screenshot(path=IMG_PATH)
    img = Image.open(IMG_PATH)
    w, h = img.size
    img.crop((0, 0, int(w * 0.70), h)).save(IMG_PATH)
    logger.info(f"[+] CAPTCHA image saved to {IMG_PATH}")

def captcha_failed(page):
    return page.locator("text=The captcha entered is incorrect.").count() > 0

def refresh_captcha(page):
    try:
        page.locator("#refresh-img").click()
    except Exception as e:
        logger.error(f"[!] Could not refresh CAPTCHA: {e}")

def solve_captcha_with_retries(page, submit_button_text="Submit") -> bool:
    for refresh_count in range(1, MAX_CAPTCHA_REFRESHES + 1):
        try:
            fetch_captcha_image(page)
        except Exception as e:
            logger.error(f"[!] Could not fetch CAPTCHA: {e}")
            return False

        candidates = solve_captcha(IMG_PATH)
        logger.info(f"[+] {len(candidates)} captcha candidate(s) to try")

        for candidate in candidates:
            try:
                captcha_input = page.locator("input[type='text']:visible").last

                captcha_input.click()
                captcha_input.fill("")
                captcha_input.press_sequentially(candidate)

                page.locator("button:visible", has_text=submit_button_text).first.click(timeout=5000)
                page.wait_for_load_state("networkidle")
            except Exception as e:
                logger.error(f"[!] Could not submit candidate word '{candidate}': {e}")

            if not captcha_failed(page):
                page.wait_for_load_state("networkidle")
                logger.info(f"[+] Captcha succeeded with word: '{candidate}'.")
                return True

            logger.info(f"[-] Candidate word failed: '{candidate}'")

        if refresh_count < MAX_CAPTCHA_REFRESHES:
            logger.info("[!] All candidates failed — refreshing CAPTCHA")
            try:
                page.locator("#refresh-img").click()
            except Exception as e:
                logger.error(f"[!] Could not refresh CAPTCHA: {e}")
                return False

    logger.error("[!] Exhausted all refreshes — CAPTCHA failed")
    return False
