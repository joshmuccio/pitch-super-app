import os
import asyncio
import random
from playwright.async_api import async_playwright
try:
    from playwright_stealth import Stealth
    stealth = Stealth()
except ImportError:
    # Fallback if stealth is not available
    class MockStealth:
        async def apply_stealth_async(self, page):
            pass
    stealth = MockStealth()
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel

class LinkedInPost(BaseModel):
    founder_id: Optional[str] = None
    company_id: Optional[str] = None
    post_text: str
    post_url: Optional[str] = None
    posted_at: str

class ScrapePayload(BaseModel):
    linkedin_url: str
    founder_id: Optional[str] = None
    company_id: Optional[str] = None
    start_date: str  # "YYYY-MM-DD"
    max_scrolls: Optional[int] = 10  # Limit scrolling to prevent timeouts

class LinkedInScraper:
    """LinkedIn scraper service using Playwright"""
    
    def __init__(self):
        # Load environment variables explicitly
        from dotenv import load_dotenv
        load_dotenv()
        
        self.linkedin_user = os.getenv("LINKEDIN_USER")
        self.linkedin_pass = os.getenv("LINKEDIN_PASS")
        
        # Debug: Print what we actually got
        print(f"🔐 LinkedIn credentials loaded - User: {bool(self.linkedin_user)}, Pass: {bool(self.linkedin_pass)}")
        if self.linkedin_user:
            print(f"📧 User email: {self.linkedin_user[:5]}***")  # Show first 5 chars only
        
    async def scrape_profile_posts(self, payload: ScrapePayload) -> Tuple[List[LinkedInPost], Dict[str, Any]]:
        """
        Scrape LinkedIn posts from a founder's profile (optimized for timeouts)
        
        Args:
            payload: ScrapePayload containing URL, IDs, and start date
            
        Returns:
            Tuple of (List of LinkedInPost objects, debug_info dict)
        """
        debug_info = {
            "step": "starting",
            "login_attempted": False,
            "login_success": False,
            "profile_loaded": False,
            "articles_found": 0,
            "html_length": 0,
            "soup_articles": 0,
            "date_filtered": 0,
            "final_posts": 0,
            "errors": []
        }
        
        start_dt = datetime.fromisoformat(payload.start_date)
        
        # Use persistent context to maintain login session
        async with async_playwright() as pw:
            # Detect if running in production (Render) or locally
            is_production = bool(os.getenv("RENDER")) or bool(os.getenv("RAILWAY_ENVIRONMENT")) or not os.getenv("HOME", "").startswith("/Users/")
            
            # Set environment variables for headless mode in containers
            if is_production:
                os.environ["DISPLAY"] = ":99"  # Virtual display for headless mode
            
            browser = await pw.chromium.launch_persistent_context(
                user_data_dir="/tmp/linkedin_cache",
                headless=is_production,  # Run headless in production, headed locally for debugging
                slow_mo=0 if is_production else 100,  # No slow motion in production
                args=[
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',  # Helps with Docker
                    '--disable-blink-features=AutomationControlled',  # Hide automation
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    # Additional args for headless mode in containers
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps',
                    '--no-first-run'
                ] if is_production else [
                    '--no-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ],
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            
            # Get the existing page or create a new one
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # Apply stealth mode to avoid detection
            await stealth.apply_stealth_async(page)
            
            # Set page timeout to 15 seconds for faster operation
            page.set_default_timeout(15000)
            
            try:
                debug_info["step"] = "checking_login_status"
                
                # Check if we're already logged in by going to feed
                await page.goto("https://www.linkedin.com/feed", timeout=15000)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                current_url = page.url
                debug_info["initial_url"] = current_url
                
                if "login" in current_url or "challenge" in current_url:
                    # Need to log in
                    debug_info["step"] = "login_required"
                    debug_info["login_attempted"] = True
                    
                    await page.goto("https://www.linkedin.com/login", timeout=15000)
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    
                    # Validate credentials before attempting to fill
                    if not self.linkedin_user or not self.linkedin_pass:
                        debug_info["errors"].append(f"Missing credentials - user: {bool(self.linkedin_user)}, pass: {bool(self.linkedin_pass)}")
                        debug_info["step"] = "missing_credentials"
                        return [], debug_info
                    
                    # Fill login form with more realistic timing
                    try:
                        # Wait for form to be ready
                        await page.wait_for_selector("#username", timeout=10000)
                        await page.wait_for_selector("#password", timeout=10000)
                        
                        # Type slowly to mimic human behavior
                        await page.fill("#username", "")  # Clear first
                        await page.type("#username", self.linkedin_user, delay=50)  # 50ms between keystrokes
                        await page.wait_for_timeout(500)  # Brief pause
                        
                        await page.fill("#password", "")  # Clear first
                        await page.type("#password", self.linkedin_pass, delay=50)  # 50ms between keystrokes
                        await page.wait_for_timeout(1000)  # Pause before clicking
                        
                        # Click submit button
                        await page.click("button[type=submit]")
                        debug_info["login_form_filled"] = True
                        
                    except Exception as e:
                        debug_info["errors"].append(f"Login form error: {str(e)}")
                        debug_info["step"] = "login_form_error"
                        return [], debug_info
                    
                    debug_info["step"] = "login_waiting"
                    
                    # Wait for login completion with better error detection
                    try:
                        # Wait longer for login to complete
                        await page.wait_for_timeout(3000)  # Wait 3 seconds for processing
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)  # 30 second timeout
                        
                        # Check current URL and page content for various scenarios
                        current_url = page.url
                        page_content = await page.content()
                        
                        debug_info["post_login_url"] = current_url
                        
                        # Check for various login failure scenarios
                        if "login" in current_url:
                            debug_info["errors"].append("Still on login page - login failed")
                            debug_info["step"] = "login_failed"
                        elif "challenge" in current_url:
                            debug_info["errors"].append("LinkedIn challenge/verification required")
                            debug_info["step"] = "challenge_required"
                        elif "captcha" in page_content.lower():
                            debug_info["errors"].append("CAPTCHA verification required")
                            debug_info["step"] = "captcha_required"
                        elif "verification" in page_content.lower():
                            debug_info["errors"].append("Email/phone verification required")
                            debug_info["step"] = "verification_required"
                        elif "security" in page_content.lower() and "check" in page_content.lower():
                            debug_info["errors"].append("Security check required")
                            debug_info["step"] = "security_check_required"
                        elif "feed" in current_url or "linkedin.com/in/" in current_url:
                            debug_info["login_success"] = True
                            debug_info["step"] = "login_success"
                        else:
                            debug_info["errors"].append(f"Unknown login state - URL: {current_url}")
                            debug_info["step"] = "login_unknown"
                            
                    except Exception as e:
                        debug_info["errors"].append(f"Login wait timeout: {str(e)}")
                        debug_info["step"] = "login_timeout"
                        
                else:
                    # Already logged in
                    debug_info["login_success"] = True
                    debug_info["step"] = "already_logged_in"
                
                # If login failed, try to continue anyway to see what we can access
                if not debug_info.get("login_success", False):
                    debug_info["errors"].append("Continuing without successful login - may have limited access")
                
                debug_info["step"] = "navigating_to_profile"
                
                # Navigate to profile activity page (where posts are actually located)
                activity_url = payload.linkedin_url.rstrip('/') + '/recent-activity/'
                
                try:
                    await page.goto(activity_url, timeout=15000)
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    debug_info["profile_loaded"] = True
                except Exception as e:
                    debug_info["errors"].append(f"Failed to load activity page: {str(e)}")
                    
                    # Fallback: try the main profile page
                    try:
                        await page.goto(payload.linkedin_url, timeout=15000)
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        debug_info["profile_loaded"] = True
                        debug_info["fallback_to_main_profile"] = True
                        activity_url = payload.linkedin_url
                    except Exception as e2:
                        debug_info["errors"].append(f"Failed to load main profile page: {str(e2)}")
                        debug_info["profile_loaded"] = False
                        debug_info["step"] = "profile_load_failed"
                        return [], debug_info
                
                # Reduced wait time for faster operation
                await page.wait_for_timeout(1500)  # Reduced from 3 seconds to 1.5 seconds
                
                # Don't wait for selectors - just proceed to capture HTML like timing test does
                debug_info["timing_test_approach"] = True
                
                debug_info["activity_url"] = activity_url
                debug_info["step"] = "activity_page_loaded"
                
                # Wait for initial content load and count articles/posts
                # Try multiple selectors for LinkedIn activity page posts (based on testing)
                selectors_to_try = [
                    ".feed-shared-update-v2",  # LinkedIn feed updates (WORKS - found 5)
                    ".occludable-update",  # LinkedIn update containers (WORKS - found 8)
                    "[data-urn*='activity']",  # Activity URNs (WORKS - found 5)
                    ".artdeco-card",  # LinkedIn card components (WORKS - found 20)
                    "article",  # General posts (fallback)
                ]
                
                articles_found = False
                for selector in selectors_to_try:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)  # Reduced timeout
                        articles_count = await page.eval_on_selector_all(selector, "els => els.length")
                        debug_info["articles_found"] = articles_count
                        debug_info["articles_selector"] = selector
                        debug_info["step"] = "articles_found"
                        print(f"✅ Found {articles_count} posts using selector: {selector}")
                        articles_found = True
                        break
                    except Exception as e:
                        print(f"❌ Selector '{selector}' failed: {str(e)[:100]}")
                        debug_info["errors"].append(f"Selector '{selector}' failed: {str(e)}")
                        continue
                
                if not articles_found:
                    debug_info["step"] = "no_articles"
                
                debug_info["step"] = "scrolling"
                
                # Fast scrolling strategy - minimal waits, get content quickly
                scroll_count = 0
                max_scrolls = min(payload.max_scrolls or 5, 5)  # Limit to 5 scrolls max for speed
                
                for scroll_count in range(max_scrolls):
                    # Fast scroll down
                    await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")  # Scroll 2x height for speed
                    
                    # Minimal wait - just 1 second instead of 3-5 seconds
                    await page.wait_for_timeout(1000)
                    debug_info[f"scroll_{scroll_count}_completed"] = True
                    
                    # Quick check for any posts without waiting for specific selectors
                    try:
                        post_count = await page.eval_on_selector_all("article, .feed-shared-update-v2, .occludable-update", "els => els.length")
                        debug_info[f"scroll_{scroll_count}_posts_found"] = post_count
                        if post_count > 20:  # If we have enough posts, stop scrolling
                            debug_info["early_stop_reason"] = f"Found {post_count} posts"
                            break
                    except:
                        pass  # Continue even if count fails
                
                debug_info["step"] = "scrolling_complete"
                debug_info["scrolls_performed"] = scroll_count
                
                # Get page content for parsing
                html = await page.content()
                debug_info["html_length"] = len(html)
                debug_info["step"] = "html_extracted"
                
            except Exception as e:
                debug_info["errors"].append(f"Scraping error: {str(e)}")
                debug_info["step"] = "scraping_error"
                try:
                    html = await page.content()  # Get whatever content we have
                    debug_info["html_length"] = len(html)
                except:
                    html = ""
                    debug_info["html_length"] = 0
                
            finally:
                await browser.close()
        
        debug_info["step"] = "parsing_html"
        
        # Parse HTML with BeautifulSoup using LinkedIn activity selectors
        soup = BeautifulSoup(html, "html.parser")
        
        # Try the selectors we know work, in order of preference
        activity_posts = []
        selectors_tried = []
        
        for selector in [".feed-shared-update-v2", ".occludable-update", "[data-urn*='activity']", ".artdeco-card"]:
            posts = soup.select(selector)
            selectors_tried.append(f"{selector}: {len(posts)}")
            if posts:
                activity_posts = posts
                debug_info["soup_selector_used"] = selector
                break
        
        debug_info["soup_selectors_tried"] = selectors_tried
        debug_info["soup_articles"] = len(activity_posts)
        
        posts = []
        
        for i, article in enumerate(activity_posts):
            # Try multiple ways to find time information
            time_elem = None
            datetime_attr = None
            
            # Method 1: Direct time element
            time_elem = article.find("time")
            if time_elem and hasattr(time_elem, 'attrs') and time_elem.attrs:
                datetime_attr = time_elem.attrs.get("datetime")
            
            # Method 2: Look for time element anywhere in the article
            if not datetime_attr:
                all_times = article.find_all("time")
                for t in all_times:
                    if hasattr(t, 'attrs') and t.attrs and t.attrs.get("datetime"):
                        time_elem = t
                        datetime_attr = t.attrs.get("datetime")
                        break
            
            # Method 3: Look for aria-label with date info
            if not datetime_attr:
                for elem in article.find_all(attrs={"aria-label": True}):
                    aria_label = elem.get("aria-label", "")
                    if any(word in aria_label.lower() for word in ["ago", "day", "week", "month", "year"]):
                        debug_info["errors"].append(f"Article {i}: Found aria-label with time: {aria_label[:100]}")
                        # For now, skip these posts as we can't parse relative dates easily
                        continue
            
            if not datetime_attr:
                debug_info["errors"].append(f"Article {i}: No time element found after all methods")
                continue
                
            try:
                posted = datetime.fromisoformat(datetime_attr)
                if posted < start_dt:
                    debug_info["date_filtered"] += 1
                    continue
            except ValueError as e:
                debug_info["errors"].append(f"Article {i}: Invalid date format: {datetime_attr}")
                continue
                
            # Extract post URL
            link_elem = article.select_one("a[href*='/feed/update']")
            post_url = None
            if link_elem and hasattr(link_elem, 'get'):
                href = link_elem.get("href")
                if href and isinstance(href, str):
                    post_url = href.split("?")[0]
            
            # Extract and clean post text
            post_text = " ".join(article.get_text(" ", strip=True).split())
            
            posts.append(LinkedInPost(
                founder_id=payload.founder_id,
                company_id=payload.company_id,
                post_text=post_text,
                post_url=post_url,
                posted_at=posted.isoformat()
            ))
        
        debug_info["final_posts"] = len(posts)
        debug_info["step"] = "parsing_complete"
        
        return posts, debug_info

# Global scraper instance
linkedin_scraper = LinkedInScraper()

async def scrape_linkedin_posts(payload: ScrapePayload) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main scraping function that returns raw dictionaries (timeout-optimized)
    
    Args:
        payload: ScrapePayload containing scraping parameters
        
    Returns:
        Tuple of (List of post dictionaries, debug_info dict)
    """
    try:
        # Increase timeout to 3 minutes for production environment
        posts, debug_info = await asyncio.wait_for(
            linkedin_scraper.scrape_profile_posts(payload),
            timeout=180.0  # 3 minutes instead of 90 seconds
        )
        return [post.dict() for post in posts], debug_info
    except asyncio.TimeoutError:
        return [{"error": "Scraping timed out after 3 minutes"}], {"step": "timeout", "errors": ["Overall timeout"]}
    except Exception as e:
        return [{"error": f"Scraping failed: {str(e)}"}], {"step": "exception", "errors": [str(e)]} 