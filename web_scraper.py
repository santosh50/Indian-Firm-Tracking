import os
import logging
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from PIL import Image

from captcha_solver import solve_captcha

TEST_CIN = "U74999GJ1995PTC025739"
AUTH_FILE = "auth_state.json"
MCA_HOME_URL = "https://www.mca.gov.in/content/mca/global/en/home.html"
MCA_LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"
IMG_PATH = "captcha.png"
MAX_CAPTCHA_REFRESHES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scraper.log"),
    ],
)

logger = logging.getLogger(__name__)

def is_logged_in(page) -> bool:
    try:
        page.locator("button", has_text="Hello").first.wait_for(state="visible", timeout=5000)
        return True
    except Exception:
        return False

def fetch_captcha_image(page):
    img_selector = "img[src*='captcha']"
    spinner_selector = "[role='status']"

    logger.info("Fetching captcha image")
    captcha_element = page.wait_for_selector(
        img_selector,
        state="visible",
    )

    page.wait_for_selector(spinner_selector, state="visible", timeout=2000)
    page.wait_for_selector(spinner_selector, state="hidden", timeout=10000)
        
    captcha_element.screenshot(path=IMG_PATH)
    img = Image.open(IMG_PATH)
    w, h = img.size
    img.crop((0, 0, int(w * 0.70), h)).save(IMG_PATH)
    logger.info(f"[+] CAPTCHA image saved to {IMG_PATH}")

def captcha_failed(page):
    try:
        page.wait_for_selector(
            "text=The captcha entered is incorrect.",
            timeout=3000,
        )
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
    
    for refresh_count in range(1, MAX_CAPTCHA_REFRESHES + 1):
        try:
            fetch_captcha_image(page)
        except Exception as e:
            logger.error(f"[!] Could not fetch CAPTCHA: {e}")
            return

        candidates = solve_captcha(IMG_PATH)
        logger.info(f"[+] {len(candidates)} candidate(s) to try: {candidates}")

        for candidate in candidates:
            try:
                captcha_input = page.locator("input[type='text']:visible").last

                captcha_input.click()
                captcha_input.fill(candidate)

                page.get_by_text("Continue", exact=True).first.click(timeout=5000)
            except Exception as e:
                logger.error(f"[!] Could not submit word'{candidate}': {e}")

            if not captcha_failed(page):
                page.wait_for_load_state("networkidle")
                context.storage_state(path=AUTH_FILE)
                logger.info(f"[+] Captcha succeeded with word: '{candidate}'.")
                input("\n[?] Enter the OTP in the browser window, then press Enter here to continue...")

                if is_logged_in(page):
                    context.storage_state(path=AUTH_FILE)
                    logger.info("[+] Login succeeded. Auth state saved")
                else:
                    logger.error("[!] OTP step failed")
                
                return

            logger.info(f"[-] Candidate failed: '{candidate}'")

        if refresh_count < MAX_CAPTCHA_REFRESHES:
            logger.info("[!] All candidates failed — refreshing CAPTCHA")
            try:
                page.locator("#refresh-img").click()
            except Exception as e:
                logger.error(f"[!] Could not refresh CAPTCHA: {e}")
                return

    logger.info("[!] Exhausted all refreshes — login failed")
    

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

        logger.info("Opening MCA home page")
        page.goto(MCA_HOME_URL)
        page.wait_for_load_state("domcontentloaded")

        if is_logged_in(page):
            logger.info("[+] Already logged in.")
        else:
            logger.info("[-] Login required")
            login(page, context)

        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    main()
