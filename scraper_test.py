import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

CIN = "U74999GJ1995PTC025739"
AUTH_FILE = "auth_state.json"
MCA_HOME_URL = "https://www.mca.gov.in/content/mca/global/en/home.html"
MCA_LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"

def is_logged_in(page) -> bool:
    hello_button = page.locator("button", has_text="Hello").first
    try:
        return hello_button.is_visible(timeout=4000)
    except Exception:
        return False

def solve_captcha(page):
    captcha_element = page.wait_for_selector(
        "img[src*='captcha']",
        state="visible",
    )

    if os.path.exists("captcha.png"):
        os.remove("captcha.png")

    time.sleep(3)
    
    captcha_element.screenshot(path="captcha.png")
    print("[+] CAPTCHA image saved to captcha.png")

def login(page, context):
    print("Opening MCA login page...")
    page.goto(MCA_LOGIN_URL, wait_until="domcontentloaded")

    load_dotenv()
    user_id = os.environ.get("MCA_USER_ID", "")
    password = os.environ.get("MCA_PASSWORD", "")

    print("Filling in User ID and Password...")
    try:
        user_input = page.locator("input[type='text']:visible").nth(1)
        pass_input = page.locator("input[type='password']:visible").first
        
        user_input.click()
        user_input.fill(user_id)

        pass_input.click()
        pass_input.fill(password)
    except Exception as e:
        print(f"[!] Could not fill credentials: {e}")
        return

    print("Clicking Login...")
    try:
        page.get_by_text("Login", exact=True).first.click(timeout=5000)
    except Exception as e:
        print(f"[!] Could not click Login: {e}")
        return

    print("Fetching Captcha...")
    try:
        solve_captcha(page)
    except Exception as e:
        print(f"[!] Could not fetch CAPTCHA: {e}")
        return


def main():
    with sync_playwright() as p:
        print("Launching Firefox browser...")
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

        print("Opening MCA home page...")
        page.goto(MCA_HOME_URL)
        page.wait_for_load_state("domcontentloaded")

        if is_logged_in(page):
            print("[+] Already logged in.")
        else:
            print("[-] Login required")
            login(page, context)

        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    main()
