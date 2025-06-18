import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class LinkedInPost(BaseModel):
    founder_id: Optional[str] = None  # UUID as string (will be converted by Supabase)
    post_text: str
    post_url: Optional[str] = None
    posted_at: str  # ISO format datetime string for timestamptz

class ScrapePayload(BaseModel):
    linkedin_url: str
    founder_id: Optional[str] = None
    company_id: Optional[str] = None  # Not stored in linkedin_posts table, just for reference
    start_date: str  # "YYYY-MM-DD"
    max_scrolls: Optional[int] = 10  # Limit scrolling to prevent timeouts

class LinkedInScraper:
    """LinkedIn scraper service using Playwright"""
    
    def __init__(self):
        self.linkedin_user = os.getenv("LINKEDIN_USER")
        self.linkedin_pass = os.getenv("LINKEDIN_PASS")
        
    async def scrape_profile_posts(self, payload: ScrapePayload) -> List[LinkedInPost]:
        """
        Scrape LinkedIn posts from a founder's profile (optimized for timeouts)
        
        Args:
            payload: ScrapePayload containing URL, IDs, and start date
            
        Returns:
            List of LinkedInPost objects
        """
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
                # Login to LinkedIn (with timeout)
                await page.goto("https://www.linkedin.com/login", timeout=15000)
                await page.fill("#username", self.linkedin_user)
                await page.fill("#password", self.linkedin_pass)
                await page.click("button[type=submit]")
                
                # Wait for login completion (reduced timeout)
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                except:
                    pass  # Continue even if timeout - LinkedIn might have loaded
                
                # Navigate to profile (with timeout)
                await page.goto(payload.linkedin_url, timeout=15000)
                
                # Wait for initial content load
                try:
                    await page.wait_for_selector("article", timeout=10000)
                except:
                    pass  # Continue even if no articles found initially
                
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
                            
                    except Exception:
                        # If we can't evaluate times, continue scrolling
                        pass
                    
                    scroll_count += 1
                
                # Get page content for parsing
                html = await page.content()
                
            except Exception as e:
                print(f"Scraping error: {e}")
                html = await page.content()  # Get whatever content we have
                
            finally:
                await browser.close()
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        posts = []
        
        for article in soup.select("article"):
            time_elem = article.find("time")
            if not time_elem:
                continue
                
            datetime_attr = time_elem.attrs.get("datetime") if time_elem.attrs else None
            if not datetime_attr:
                continue
                
            try:
                posted = datetime.fromisoformat(datetime_attr)
                if posted < start_dt:
                    continue
            except ValueError:
                continue  # Skip invalid dates
                
            # Extract post URL
            link_elem = article.select_one("a[href*='/feed/update']")
            post_url = None
            if link_elem and hasattr(link_elem, 'get'):
                href = link_elem.get("href")
                if href and isinstance(href, str):
                    post_url = href.split("?")[0]
                    # Ensure we have a full LinkedIn URL
                    if not post_url.startswith("https://"):
                        post_url = f"https://www.linkedin.com{post_url}"
            
            # Extract and clean post text
            post_text = " ".join(article.get_text(" ", strip=True).split())
            
            # Only add posts that have meaningful content
            if post_text and len(post_text.strip()) > 10:
                posts.append(LinkedInPost(
                    founder_id=payload.founder_id,
                    post_text=post_text,
                    post_url=post_url,
                    posted_at=posted.isoformat()  # ISO format for Supabase timestamptz
                ))
        
        return posts

# Global scraper instance
linkedin_scraper = LinkedInScraper()

async def scrape_linkedin_posts(payload: ScrapePayload) -> List[Dict[str, Any]]:
    """
    Main scraping function that returns raw dictionaries for Supabase insertion
    
    Args:
        payload: ScrapePayload containing scraping parameters
        
    Returns:
        List of post dictionaries formatted for Supabase
    """
    try:
        # Add overall timeout of 2 minutes for the entire operation
        posts = await asyncio.wait_for(
            linkedin_scraper.scrape_profile_posts(payload),
            timeout=120.0
        )
        # Convert to dictionaries for Supabase insertion
        return [post.dict() for post in posts]
    except asyncio.TimeoutError:
        return [{"error": "Scraping timed out after 2 minutes"}]
    except Exception as e:
        return [{"error": f"Scraping failed: {str(e)}"}] 