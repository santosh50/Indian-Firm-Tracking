import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"

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
    print("[DEBUG] Fetching credentials")
    load_dotenv()
    user_id = os.environ.get("MCA_USER_ID", "")
    password = os.environ.get("MCA_PASSWORD", "")

    print("[DEBUG] Filling credentials")
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

    print("[DEBUG] Clicking Login")
    try:
        page.get_by_text("Login", exact=True).first.click(timeout=5000)
    except Exception as e:
        print(f"[!] Could not click Login: {e}")
        return

    print("[DEBUG] Fetching CAPTCHA image")
    try:
        solve_captcha(page)
    except Exception as e:
        print(f"[!] Could not fetch CAPTCHA: {e}")
        return
    

def main():
    with sync_playwright() as p:
        print("[DEBUG] Launching firefox browser")
        browser = p.firefox.launch(headless=False)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata"
        )

        print("[DEBUG] Opening MCA Login page")
        page = context.new_page()
        page.goto(LOGIN_URL)
        page.wait_for_load_state("domcontentloaded")

        print("[DEBUG] Attempting Login")
        login(page, context)

        input("Press Enter to close browser")
        browser.close()

if __name__ == "__main__":
    main()
