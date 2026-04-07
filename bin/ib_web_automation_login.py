#!/usr/bin/env python3
"""
Interactive Brokers Web Portal Automation
Browser-based login automation using Playwright
"""

import asyncio
import sys
import os
import logging
import time
from typing import Optional, Dict
import json

# Add virtual environment path
sys.path.append("/home/davidsanker/trading_bot_venv/lib/python3.11/site-packages")

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from playwright._impl._api_structures import ProxySettings
except ImportError:
    print("❌ Playwright not installed. Run: pip install playwright")
    sys.exit(1)

class IBWebPortalAutomator:
    """Interactive Brokers Web Portal Automation"""

    def __init__(self):
        self.credentials = {
            "username": "amakua444",
            "password": "YOUR_IB_PASSWORD"
        }
        self.login_url = "https://ndcdyn.interactivebrokers.com/sso/Login"
        self.headless = True   # Set to True for production, False for debugging

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def create_browser_context(self, playwright) -> tuple[Browser, BrowserContext, Page]:
        """Create browser context with proper settings"""
        self.logger.info("🌐 Creating browser context...")

        # Browser launch options
        browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
                "--window-size=1920,1080"
            ]
        )

        # Create context with anti-detection measures
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            java_script_enabled=True
        )

        # Create page
        page = await context.new_page()

        return browser, context, page

    async def handle_cookie_consent(self, page: Page) -> bool:
        """Handle cookie consent dialogs"""
        try:
            self.logger.info("🍪 Checking for cookie consent...")

            # Wait for cookie consent to appear
            cookie_selectors = [
                "button[data-testid='accept-cookies']",
                "button[id='accept-cookies']",
                "button:has-text('Accept')",
                "button:has-text('I Accept')",
                ".cookie-accept button",
                "#cookie-consent button"
            ]

            for selector in cookie_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    await page.click(selector)
                    self.logger.info("✅ Cookie consent accepted")
                    return True
                except:
                    continue

            self.logger.info("ℹ️ No cookie consent found or required")
            return True

        except Exception as e:
            self.logger.warning(f"⚠️ Cookie consent handling failed: {e}")
            return True

    async def handle_login_form(self, page: Page) -> bool:
        """Handle the login form interaction"""
        try:
            self.logger.info("🔐 Handling login form...")

            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Multiple selector strategies for username field
            username_selectors = [
                "input[name='username']",
                "input[name='user']",
                "input[name='login']",
                "input[id='username']",
                "input[id='user']",
                "input[type='text']",
                "input[placeholder*='username' i]",
                "input[placeholder*='user' i]",
                ".username input",
                "#username"
            ]

            username_field = None
            for selector in username_selectors:
                try:
                    username_field = await page.wait_for_selector(selector, timeout=3000)
                    if username_field:
                        break
                except:
                    continue

            if not username_field:
                self.logger.error("❌ Username field not found")
                # Take screenshot for debugging
                await page.screenshot(path="/tmp/ib_login_debug.png")
                return False

            self.logger.info("✅ Username field found")
            await username_field.click()
            await username_field.fill("")  # Clear the field
            await username_field.type(self.credentials["username"])
            await page.wait_for_timeout(500)

            # Find password field
            password_selectors = [
                "input[name='password']",
                "input[name='pass']",
                "input[name='pwd']",
                "input[id='password']",
                "input[id='pass']",
                "input[type='password']",
                "input[placeholder*='password' i]",
                ".password input",
                "#password"
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    password_field = await page.wait_for_selector(selector, timeout=3000)
                    if password_field:
                        break
                except:
                    continue

            if not password_field:
                self.logger.error("❌ Password field not found")
                await page.screenshot(path="/tmp/ib_login_debug.png")
                return False

            self.logger.info("✅ Password field found")
            await password_field.click()
            await password_field.fill("")  # Clear the field
            await password_field.type(self.credentials["password"])
            await page.wait_for_timeout(500)

            return True

        except Exception as e:
            self.logger.error(f"❌ Login form handling failed: {e}")
            await page.screenshot(path="/tmp/ib_login_debug.png")
            return False

    async def submit_login(self, page: Page) -> bool:
        """Submit the login form"""
        try:
            self.logger.info("🚀 Submitting login...")

            # Look for submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Log In')",
                "button:has-text('Login')",
                "button:has-text('Sign In')",
                "button:has-text('Continue')",
                ".login-button",
                "#login-button",
                "button[data-testid='login-submit']"
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(selector, timeout=3000)
                    if submit_button:
                        break
                except:
                    continue

            if submit_button:
                await submit_button.click()
                self.logger.info("✅ Login form submitted")
                return True
            else:
                # Try pressing Enter as fallback
                await page.keyboard.press("Enter")
                self.logger.info("✅ Login submitted with Enter key")
                return True

        except Exception as e:
            self.logger.error(f"❌ Login submission failed: {e}")
            return False

    async def handle_2fa_verification(self, page: Page) -> bool:
        """Handle 2FA verification"""
        try:
            self.logger.info("📱 Checking for 2FA verification...")

            # Wait for possible 2FA page
            await page.wait_for_timeout(5000)

            # Check for 2FA indicators
            two_fa_indicators = [
                "Two-factor authentication",
                "2FA",
                "Verification code",
                "Security code",
                "Mobile device",
                "Authenticator app"
            ]

            page_content = await page.content()
            for indicator in two_fa_indicators:
                if indicator.lower() in page_content.lower():
                    self.logger.info(f"📱 2FA page detected: {indicator}")

                    # Wait for user to complete 2FA
                    self.logger.info("⏳ Waiting for 2FA completion...")
                    self.logger.info("📱 Please complete 2FA on your mobile device")

                    # Wait for page to redirect after 2FA
                    try:
                        await page.wait_for_url(
                            lambda url: "login" not in url.lower() and "sso" not in url.lower(),
                            timeout=120000  # 2 minutes
                        )
                        self.logger.info("✅ 2FA completed successfully")
                        return True
                    except:
                        # Check if we're already logged in by looking for logout button
                        logout_selectors = [
                            "button:has-text('Log Out')",
                            "button:has-text('Logout')",
                            "a:has-text('Log Out')",
                            ".logout",
                            "#logout"
                        ]

                        for selector in logout_selectors:
                            try:
                                if await page.query_selector(selector):
                                    self.logger.info("✅ Already logged in (2FA likely completed)")
                                    return True
                            except:
                                continue

                        self.logger.warning("⚠️ 2FA status unclear - continuing")
                        return True

            self.logger.info("ℹ️ No 2FA detected")
            return True

        except Exception as e:
            self.logger.error(f"❌ 2FA handling failed: {e}")
            return False

    async def verify_login_success(self, page: Page) -> bool:
        """Verify that login was successful"""
        try:
            self.logger.info("✅ Verifying login success...")

            # Wait for page to load after login
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Check for successful login indicators
            success_indicators = [
                "Account Overview",
                "Portfolio",
                "Dashboard",
                "Balance",
                "Positions",
                "Orders",
                "Log Out",
                "Logout"
            ]

            page_content = await page.content()
            for indicator in success_indicators:
                if indicator.lower() in page_content.lower():
                    self.logger.info(f"✅ Login success confirmed: {indicator}")

                    # Get account information
                    try:
                        await page.wait_for_timeout(3000)
                        title = await page.title()
                        self.logger.info(f"📄 Page title: {title}")

                        # Take screenshot for verification
                        await page.screenshot(path="/tmp/ib_login_success.png")
                        self.logger.info("📸 Login success screenshot saved")

                        return True
                    except:
                        pass

            # Fallback: check if URL changed from login page
            current_url = page.url
            if "login" not in current_url.lower() and "sso" not in current_url.lower():
                self.logger.info(f"✅ Login appears successful (URL: {current_url})")
                return True

            self.logger.error("❌ Login success could not be verified")
            await page.screenshot(path="/tmp/ib_login_failed.png")
            return False

        except Exception as e:
            self.logger.error(f"❌ Login verification failed: {e}")
            return False

    async def extract_session_info(self, page: Page) -> Dict:
        """Extract session information for future use"""
        try:
            self.logger.info("📊 Extracting session information...")

            # Get cookies
            cookies = await page.context.cookies()

            # Get local storage
            local_storage = await page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }
            """)

            # Get session storage
            session_storage = await page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            }
            """)

            session_info = {
                "url": page.url,
                "title": await page.title(),
                "cookies": cookies,
                "local_storage": local_storage,
                "session_storage": session_storage,
                "timestamp": time.time()
            }

            # Save session info
            with open("/tmp/ib_session_info.json", "w") as f:
                json.dump(session_info, f, indent=2, default=str)

            self.logger.info("✅ Session information extracted and saved")
            return session_info

        except Exception as e:
            self.logger.error(f"❌ Session extraction failed: {e}")
            return {}

    async def automate_login(self) -> bool:
        """Main automated login process"""
        self.logger.info("🚀 Starting IB web portal automated login...")

        async with async_playwright() as playwright:
            browser, context, page = await self.create_browser_context(playwright)

            try:
                # Step 1: Navigate to login page
                self.logger.info(f"🌐 Navigating to {self.login_url}")
                await page.goto(self.login_url)
                await page.wait_for_load_state("networkidle", timeout=15000)

                # Step 2: Handle cookie consent
                if not await self.handle_cookie_consent(page):
                    self.logger.warning("⚠️ Cookie consent handling failed, continuing...")

                # Step 3: Handle login form
                if not await self.handle_login_form(page):
                    self.logger.error("❌ Login form handling failed")
                    return False

                # Step 4: Submit login
                if not await self.submit_login(page):
                    self.logger.error("❌ Login submission failed")
                    return False

                # Step 5: Handle 2FA verification
                if not await self.handle_2fa_verification(page):
                    self.logger.error("❌ 2FA handling failed")
                    return False

                # Step 6: Verify login success
                if not await self.verify_login_success(page):
                    self.logger.error("❌ Login verification failed")
                    return False

                # Step 7: Extract session information
                session_info = await self.extract_session_info(page)

                self.logger.info("🎉 IB web portal login completed successfully!")
                self.logger.info(f"📊 Logged in at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                self.logger.info("📸 Screenshots saved to /tmp/ directory")
                self.logger.info("📋 Session info saved to /tmp/ib_session_info.json")

                return True

            except Exception as e:
                self.logger.error(f"❌ Automated login failed: {e}")
                await page.screenshot(path="/tmp/ib_login_error.png")
                return False

            finally:
                # Keep browser open for 30 seconds for manual verification if needed
                if not self.headless:
                    self.logger.info("🌐 Browser will remain open for 30 seconds for manual verification...")
                    await asyncio.sleep(30)

                await context.close()
                await browser.close()

def main():
    """Main entry point"""
    automator = IBWebPortalAutomator()

    try:
        success = asyncio.run(automator.automate_login())

        if success:
            print("🎉 IB Web Portal login automation successful!")
            print("📊 Session information extracted and saved")
            print("📸 Screenshots captured for verification")
        else:
            print("❌ IB Web Portal login automation failed")
            print("🔧 Check screenshots in /tmp/ directory for debugging")

        return success

    except KeyboardInterrupt:
        print("⏹️ Automation process interrupted")
        return False
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)