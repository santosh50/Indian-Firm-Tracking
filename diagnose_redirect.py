from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        print("[DEBUG] Launching Firefox...")
        
        browser = p.firefox.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        )
        page = context.new_page()
        
        print("[DEBUG] Firefox launched")
        
        # Navigate to MCA
        login_url = "https://www.mca.gov.in/content/mca/global/en/foportal/fologin.html"
        
        print("[+] Navigating to login...")
        page.goto(login_url)
        print(f"[DEBUG] URL: {page.url}")
        
        # Monitor
        print("\n=== Monitoring (15 seconds) ===")
        for i in range(15):
            time.sleep(1)
            current_url = page.url
            status = "STABLE" if "fologin.html" in current_url else "BOUNCED"
            print(f"[{i+1:02d}s] URL: {current_url} | Status: {status}")
        
        print("\n[+] Monitoring complete.")
        input("Press ENTER to exit...")
        
        browser.close()

if __name__ == "__main__":
    main()
