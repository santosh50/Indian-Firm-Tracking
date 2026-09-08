import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

CIN = "U74999GJ1995PTC025739"
MCA_LOGIN_URL = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"

def login(page):
    print("Opening MCA login page...")
    page.goto(MCA_LOGIN_URL, wait_until="domcontentloaded")

    load_dotenv()
    user_id = os.environ.get("MCA_USER_ID", "")
    password = os.environ.get("MCA_PASSWORD", "")

    print("Filling in User ID and Password...")
    try:
        page.locator("input[type='text']:visible").nth(1).fill(user_id)
        page.locator("input[type='password']:visible").first.fill(password)
    except Exception as e:
        print(f"[!] Could not fill credentials: {e}")

    print("Logging in...")
    try:
        page.get_by_text("Login", exact=True).first.click(timeout=5000)
    except Exception as e:
        print(f"[!] Could not click Login: {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        # Intercept redirect timers selectively before DOM loads
        page.add_init_script("""
            (() => {
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

                // Selective setTimeout override using valid JS comments
                const originalSetTimeout = window.setTimeout;
                window.setTimeout = function(fn, delay, ...args) {
                    const fnStr = fn ? fn.toString() : '';
                    if (fnStr.includes('home.html')) {
                        console.log('Blocked home.html redirect timer');
                        return -1;
                    }
                    return originalSetTimeout(fn, delay, ...args);
                };
            })();
        """)

        login(page)

        input("Press Enter to close browser...")
        browser.close()

if __name__ == "__main__":
    main()
