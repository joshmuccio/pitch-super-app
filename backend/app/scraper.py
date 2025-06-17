import os
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional
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

class LinkedInScraper:
    """LinkedIn scraper service using Playwright"""
    
    def __init__(self):
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL")
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD")
        
    async def scrape_profile_posts(self, payload: ScrapePayload) -> List[LinkedInPost]:
        """
        Scrape LinkedIn posts from a founder's profile
        
        Args:
            payload: ScrapePayload containing URL, IDs, and start date
            
        Returns:
            List of LinkedInPost objects
        """
        start_dt = datetime.fromisoformat(payload.start_date)
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Login to LinkedIn
                await page.goto("https://www.linkedin.com/login")
                await page.fill("#username", self.linkedin_email)
                await page.fill("#password", self.linkedin_password)
                await page.click("button[type=submit]")
                await page.wait_for_load_state("networkidle")
                
                # Navigate to profile and scroll to collect posts
                await page.goto(payload.linkedin_url, wait_until="networkidle")
                reached_oldest = False
                
                while not reached_oldest:
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await page.wait_for_timeout(1200)
                    
                    # Check if we've reached posts older than start_date
                    times = await page.eval_on_selector_all(
                        "time",
                        "els => els.map(e => e.getAttribute('datetime'))"
                    )
                    
                    if any(datetime.fromisoformat(t) < start_dt for t in times if t):
                        reached_oldest = True
                
                # Get page content for parsing
                html = await page.content()
                
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
                
            posted = datetime.fromisoformat(datetime_attr)
            if posted < start_dt:
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
        
        return posts

# Global scraper instance
linkedin_scraper = LinkedInScraper()

async def scrape_linkedin_posts(payload: ScrapePayload) -> List[Dict[str, Any]]:
    """
    Main scraping function that returns raw dictionaries
    
    Args:
        payload: ScrapePayload containing scraping parameters
        
    Returns:
        List of post dictionaries
    """
    posts = await linkedin_scraper.scrape_profile_posts(payload)
    return [post.dict() for post in posts] 