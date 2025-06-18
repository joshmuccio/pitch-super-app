import os
import asyncio
from playwright.async_api import async_playwright
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
        self.linkedin_user = os.getenv("LINKEDIN_USER")
        self.linkedin_pass = os.getenv("LINKEDIN_PASS")
        
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
        
        # Set browser timeout to prevent hanging
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']  # Helps with Docker
            )
            page = await browser.new_page()
            
            # Set page timeout to 30 seconds
            page.set_default_timeout(30000)
            
            try:
                debug_info["step"] = "login_starting"
                
                # Login to LinkedIn (with timeout)
                await page.goto("https://www.linkedin.com/login", timeout=15000)
                await page.fill("#username", self.linkedin_user)
                await page.fill("#password", self.linkedin_pass)
                await page.click("button[type=submit]")
                
                debug_info["login_attempted"] = True
                debug_info["step"] = "login_waiting"
                
                # Wait for login completion (reduced timeout)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                    # Check if we're still on login page (login failed)
                    current_url = page.url
                    if "login" not in current_url:
                        debug_info["login_success"] = True
                        debug_info["step"] = "login_success"
                    else:
                        debug_info["errors"].append("Still on login page after attempt")
                        debug_info["step"] = "login_failed"
                except Exception as e:
                    debug_info["errors"].append(f"Login wait timeout: {str(e)}")
                    debug_info["step"] = "login_timeout"
                
                debug_info["step"] = "navigating_to_profile"
                
                # Navigate to profile (with timeout)
                await page.goto(payload.linkedin_url, timeout=15000)
                debug_info["profile_loaded"] = True
                debug_info["step"] = "profile_loaded"
                
                # Wait for initial content load and count articles
                try:
                    await page.wait_for_selector("article", timeout=10000)
                    articles_count = await page.eval_on_selector_all("article", "els => els.length")
                    debug_info["articles_found"] = articles_count
                    debug_info["step"] = "articles_found"
                except Exception as e:
                    debug_info["errors"].append(f"No articles found: {str(e)}")
                    debug_info["step"] = "no_articles"
                
                debug_info["step"] = "scrolling"
                
                # Controlled scrolling with limits
                scroll_count = 0
                max_scrolls = payload.max_scrolls or 10
                reached_oldest = False
                
                while not reached_oldest and scroll_count < max_scrolls:
                    # Scroll down
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    
                    # Reduced wait time from 1200ms to 800ms
                    await page.wait_for_timeout(800)
                    
                    # Check if we've reached posts older than start_date
                    try:
                        times = await page.eval_on_selector_all(
                            "time",
                            "els => els.map(e => e.getAttribute('datetime'))",
                            timeout=5000
                        )
                        
                        if times and any(
                            datetime.fromisoformat(t) < start_dt 
                            for t in times if t and t.strip()
                        ):
                            reached_oldest = True
                            debug_info["step"] = "reached_oldest_posts"
                            
                    except Exception as e:
                        debug_info["errors"].append(f"Time evaluation error: {str(e)}")
                    
                    scroll_count += 1
                
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
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.select("article")
        debug_info["soup_articles"] = len(articles)
        
        posts = []
        
        for i, article in enumerate(articles):
            time_elem = article.find("time")
            if not time_elem:
                debug_info["errors"].append(f"Article {i}: No time element found")
                continue
                
            datetime_attr = time_elem.attrs.get("datetime") if time_elem.attrs else None
            if not datetime_attr:
                debug_info["errors"].append(f"Article {i}: No datetime attribute")
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
        # Add overall timeout of 2 minutes for the entire operation
        posts, debug_info = await asyncio.wait_for(
            linkedin_scraper.scrape_profile_posts(payload),
            timeout=120.0
        )
        return [post.dict() for post in posts], debug_info
    except asyncio.TimeoutError:
        return [{"error": "Scraping timed out after 2 minutes"}], {"step": "timeout", "errors": ["Overall timeout"]}
    except Exception as e:
        return [{"error": f"Scraping failed: {str(e)}"}], {"step": "exception", "errors": [str(e)]} 