from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Import scraper functionality
from app.scraper import ScrapePayload, scrape_linkedin_posts

# Import embedding functionality
from app.embed import create_embedding

# Import Supabase client
from supabase import create_client

# Load environment variables
load_dotenv()

# Environment variable validation
def validate_environment():
    """Validate and report on environment variables"""
    env_status = {
        "linkedin_user": bool(os.getenv("LINKEDIN_USER")),
        "linkedin_pass": bool(os.getenv("LINKEDIN_PASS")),
        "supabase_url": bool(os.getenv("SUPABASE_URL")),
        "supabase_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "openai_key": bool(os.getenv("OPENAI_API_KEY"))
    }
    
    print("🔍 Environment Variable Status:")
    for key, status in env_status.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {key.upper()}: {'SET' if status else 'NOT SET'}")
    
    return env_status

# Initialize Supabase client with better error handling
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

sb = None
if SUPABASE_URL and SUPABASE_KEY and SUPABASE_URL != "your_supabase_url_here":
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
    except Exception as e:
        print(f"⚠️ Supabase initialization failed: {e}")
        sb = None
else:
    print("⚠️ Supabase credentials not configured - database features disabled")

# Initialize FastAPI app
app = FastAPI(
    title="Pitch Super App API",
    description="AI-powered content analysis for The Pitch Fund",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Startup event to validate environment and report status"""
    print("🚀 Starting Pitch Super App API...")
    
    # Validate environment
    env_status = validate_environment()
    
    # Check LinkedIn credentials specifically
    linkedin_user = os.getenv("LINKEDIN_USER")
    linkedin_pass = os.getenv("LINKEDIN_PASS")
    
    if linkedin_user and linkedin_pass:
        print(f"🔐 LinkedIn credentials loaded - User: True, Pass: True")
        # Mask email for security
        masked_email = linkedin_user[:5] + "***" if len(linkedin_user) > 5 else "***"
        print(f"📧 User email: {masked_email}")
    else:
        print("❌ LinkedIn credentials missing - scraping will not work")
    
    # Check if we're in a production environment
    if os.getenv("RENDER"):
        print("🌐 Running on Render")
    else:
        print("💻 Running locally")
    
    print("✅ Startup complete")

# Request/Response models
class EmbedRequest(BaseModel):
    text: str
    
class EmbedResponse(BaseModel):
    embedding: List[float]
    status: str

class SummarizeRequest(BaseModel):
    company_id: str
    start_date: str
    end_date: str
    
class SummarizeResponse(BaseModel):
    summaries: Dict[str, str]  # model_name -> summary_md
    status: str

class ScrapeResponse(BaseModel):
    inserted: int
    status: str
    debug_info: Dict[str, Any] = {}

# Health check endpoint (for Docker health check)
@app.get("/health")
async def health_check():
    """Health check endpoint with environment diagnostics"""
    env_status = validate_environment()
    
    return {
        "status": "healthy", 
        "service": "pitch-super-app-api",
        "environment": {
            "linkedin_configured": env_status["linkedin_user"] and env_status["linkedin_pass"],
            "supabase_configured": env_status["supabase_url"] and env_status["supabase_key"],
            "openai_configured": env_status["openai_key"],
            "render_environment": bool(os.getenv("RENDER"))
        },
        "features": {
            "scraping": env_status["linkedin_user"] and env_status["linkedin_pass"],
            "database": sb is not None,
            "embeddings": env_status["openai_key"]
        }
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Pitch Super App API",
        "status": "running",
        "endpoints": ["/health", "/embed", "/summarize", "/scrape"],
        "methods": {
            "/health": "GET",
            "/embed": "POST", 
            "/summarize": "POST",
            "/scrape": "GET (info) | POST (execute)"
        }
    }

# Embedding endpoint (Day 2 implementation)
@app.post("/embed", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """
    Strip HTML, chunk text, call OpenAI embeddings, return vectors
    TODO: Implement OpenAI text-embedding-3-small integration
    """
    return {
        "embedding": [0.0] * 1536,  # Placeholder 1536-dim vector
        "status": "ok"
    }

# Summarization endpoint (Day 3 implementation)
@app.post("/summarize", response_model=SummarizeResponse)
async def summarize_posts(request: SummarizeRequest):
    """
    Select posts, query pgvector for similar chunks, run LangChain Map-Reduce
    TODO: Implement multi-model summarization (gpt-4o, gpt-3.5-turbo, claude-3-sonnet)
    """
    return {
        "summaries": {
            "gpt-4o": "# Placeholder Summary\n\nThis is a placeholder summary from GPT-4o.",
            "gpt-3.5-turbo": "# Placeholder Summary\n\nThis is a placeholder summary from GPT-3.5-turbo.",
            "claude-3-sonnet": "# Placeholder Summary\n\nThis is a placeholder summary from Claude-3-Sonnet."
        },
        "status": "ok"
    }

# LinkedIn scraping endpoint (Day 1 implementation) - Now writes directly to Supabase
@app.get("/scrape")
async def scrape_info():
    """
    GET handler for /scrape endpoint - provides usage information
    """
    return {
        "message": "LinkedIn Scraper Endpoint",
        "method": "POST",
        "description": "Scrapes LinkedIn posts and writes directly to Supabase",
        "required_fields": ["linkedin_url", "founder_id", "start_date"],
        "optional_fields": ["company_id", "max_scrolls"],
        "example": {
            "linkedin_url": "https://linkedin.com/in/founder",
            "founder_id": "uuid-string",
            "start_date": "2024-01-01",
            "max_scrolls": 10
        }
    }

@app.get("/scrape/debug")
async def debug_scrape(
    linkedin_url: str = Query(..., description="LinkedIn profile URL"),
    founder_id: str = Query(None, description="Founder UUID"),
    company_id: str = Query(None, description="Company UUID"),
    start_date: str = Query(default="2023-01-01", description="Start date (YYYY-MM-DD)")
):
    """
    Debug endpoint to test LinkedIn scraping with detailed information
    """
    try:
        from .scraper import ScrapePayload, scrape_linkedin_posts
        
        payload = ScrapePayload(
            linkedin_url=linkedin_url,
            founder_id=founder_id,
            company_id=company_id,
            start_date=start_date,
            max_scrolls=5  # Limit for debugging
        )
        
        # Get posts and debug info
        posts, debug_info = await scrape_linkedin_posts(payload)
        
        # Prepare debug response
        debug_response = {
            "posts_found": len(posts),
            "posts": posts[:3],  # Show first 3 posts
            "debug_info": {
                **debug_info,
                "linkedin_credentials": {
                    "user_set": bool(os.getenv("LINKEDIN_USER")),
                    "pass_set": bool(os.getenv("LINKEDIN_PASS"))
                },
                "request_data": {
                    "linkedin_url": linkedin_url,
                    "founder_id": founder_id,
                    "company_id": company_id,
                    "start_date": start_date,
                    "max_scrolls": 5
                }
            },
            "status": "debug_complete"
        }
        
        return [debug_response]
        
    except Exception as e:
        return [{"error": f"Debug scraping failed: {str(e)}", "status": "error"}]

@app.post("/scrape")
async def scrape_linkedin(payload: ScrapePayload):
    """
    Scrape LinkedIn posts and store them in the database
    """
    try:
        # Scrape posts with debug info
        posts, debug_info = await scrape_linkedin_posts(payload)
        
        if not posts or (len(posts) == 1 and "error" in posts[0]):
            return ScrapeResponse(
                inserted=0, 
                status="no_posts_found",
                debug_info=debug_info
            )
        
        # Insert posts into database (if Supabase is available)
        inserted_count = 0
        if sb is not None:
            for post in posts:
                try:
                    # Create embedding for the post (if OpenAI is available)
                    embedding = None
                    try:
                        embedding = await create_embedding(post["post_text"])
                    except Exception as e:
                        print(f"⚠️ Embedding creation failed: {e}")
                        # Continue without embedding
                    
                    # Insert into database with conflict handling
                    result = sb.table("linkedin_posts").upsert({
                        "founder_id": post.get("founder_id"),
                        "company_id": post.get("company_id"),
                        "post_text": post["post_text"],
                        "post_url": post.get("post_url"),
                        "posted_at": post["posted_at"],
                        "embedding": embedding
                    }, on_conflict="founder_id,company_id,post_url").execute()
                    
                    if result.data:
                        inserted_count += 1
                        
                except Exception as e:
                    print(f"Error inserting post: {e}")
                    continue
        else:
            # Supabase not available - just return the posts for debugging
            inserted_count = len(posts)
        
        return ScrapeResponse(
            inserted=inserted_count, 
            status="success" if inserted_count > 0 else "no_posts_inserted",
            debug_info=debug_info
        )
        
    except Exception as e:
        return ScrapeResponse(
            inserted=0, 
            status="error",
            debug_info={"error": str(e)}
        )

@app.get("/scrape/simple")
async def simple_scrape_test(
    linkedin_url: str = Query(..., description="LinkedIn profile URL")
):
    """
    Simple test - just login and capture page content
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        linkedin_user = os.getenv("LINKEDIN_USER")
        linkedin_pass = os.getenv("LINKEDIN_PASS")
        
        if not linkedin_user or not linkedin_pass:
            return {"error": "LinkedIn credentials not configured"}
        
        async with async_playwright() as pw:
            # Detect if running in production
            is_production = bool(os.getenv("RENDER")) or bool(os.getenv("RAILWAY_ENVIRONMENT")) or not os.getenv("HOME", "").startswith("/Users/")
            
            browser = await pw.chromium.launch_persistent_context(
                user_data_dir="/tmp/linkedin_cache",
                headless=is_production,  # Run headless in production
                slow_mo=0 if is_production else 100,
                args=['--no-sandbox', '--disable-dev-shm-usage'],
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # Apply stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            # Set timeout
            page.set_default_timeout(10000)
            
            try:
                # Go to LinkedIn feed first
                await page.goto("https://www.linkedin.com/feed", timeout=15000)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                # Check if we need to login
                current_url = page.url
                if "login" in current_url:
                    await page.goto("https://www.linkedin.com/login", timeout=15000)
                    await page.fill("#username", linkedin_user)
                    await page.fill("#password", linkedin_pass)
                    await page.click("button[type=submit]")
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                
                # Try the direct activity URL first
                activity_url = linkedin_url.rstrip('/') + '/recent-activity/'
                await page.goto(activity_url, timeout=15000)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(3000)
                
                # Get page title and URL
                title = await page.title()
                url = page.url
                
                # Get page content
                html = await page.content()
                
                # Count different elements including activity-specific ones
                element_counts = {}
                selectors = [
                    "article", 
                    "div", 
                    "span", 
                    "time", 
                    "[data-urn]", 
                    ".feed-shared-update-v2",
                    "[data-urn*='activity']",  # Activity URNs
                    ".feed-shared-update",      # General feed updates
                    ".occludable-update",       # LinkedIn update containers
                    "[data-test-id*='post']",   # Post test IDs
                    ".artdeco-card",           # LinkedIn card components
                ]
                
                for selector in selectors:
                    try:
                        count = await page.eval_on_selector_all(selector, "els => els.length")
                        element_counts[selector] = count
                    except:
                        element_counts[selector] = 0
                
                # Look for activity-specific text
                activity_indicators = {}
                activity_texts = ["posted", "shared", "commented", "liked", "Activity", "Posts"]
                for text in activity_texts:
                    try:
                        count = await page.eval_on_selector_all(
                            f"text={text}", 
                            "els => els.length"
                        )
                        activity_indicators[f"text_{text}"] = count
                    except:
                        activity_indicators[f"text_{text}"] = 0
                
                return {
                    "status": "success",
                    "title": title,
                    "url": url,
                    "html_length": len(html),
                    "element_counts": element_counts,
                    "activity_indicators": activity_indicators,
                    "first_1000_chars": html[:1000]
                }
                
            finally:
                await browser.close()
                
    except Exception as e:
        return {"error": f"Simple test failed: {str(e)}"}

@app.get("/scrape/debug-timing")
async def debug_timing_test(
    linkedin_url: str = Query(..., description="LinkedIn profile URL")
):
    """
    Debug timing - capture HTML at different stages
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        from dotenv import load_dotenv
        from bs4 import BeautifulSoup
        
        # Load environment variables
        load_dotenv()
        linkedin_user = os.getenv("LINKEDIN_USER")
        linkedin_pass = os.getenv("LINKEDIN_PASS")
        
        if not linkedin_user or not linkedin_pass:
            return {"error": "LinkedIn credentials not configured"}
        
        stages = {}
        
        async with async_playwright() as pw:
            # Detect if running in production
            is_production = bool(os.getenv("RENDER")) or bool(os.getenv("RAILWAY_ENVIRONMENT")) or not os.getenv("HOME", "").startswith("/Users/")
            
            browser = await pw.chromium.launch_persistent_context(
                user_data_dir="/tmp/linkedin_cache",
                headless=is_production,  # Run headless in production
                slow_mo=0 if is_production else 100,
                args=['--no-sandbox', '--disable-dev-shm-usage'],
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # Apply stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            # Set timeout
            page.set_default_timeout(10000)
            
            try:
                # Login process
                await page.goto("https://www.linkedin.com/feed", timeout=15000)
                current_url = page.url
                if "login" in current_url:
                    await page.goto("https://www.linkedin.com/login", timeout=15000)
                    await page.fill("#username", linkedin_user)
                    await page.fill("#password", linkedin_pass)
                    await page.click("button[type=submit]")
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                
                # Navigate to activity page
                activity_url = linkedin_url.rstrip('/') + '/recent-activity/'
                await page.goto(activity_url, timeout=15000)
                
                # Stage 1: Immediately after navigation
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                html1 = await page.content()
                soup1 = BeautifulSoup(html1, "html.parser")
                stages["stage_1_after_nav"] = {
                    "feed_shared_update_v2": len(soup1.select(".feed-shared-update-v2")),
                    "occludable_update": len(soup1.select(".occludable-update")),
                    "data_urn_activity": len(soup1.select("[data-urn*='activity']")),
                    "artdeco_card": len(soup1.select(".artdeco-card")),
                }
                
                # Stage 2: After 3 second wait
                await page.wait_for_timeout(3000)
                html2 = await page.content()
                soup2 = BeautifulSoup(html2, "html.parser")
                stages["stage_2_after_3s"] = {
                    "feed_shared_update_v2": len(soup2.select(".feed-shared-update-v2")),
                    "occludable_update": len(soup2.select(".occludable-update")),
                    "data_urn_activity": len(soup2.select("[data-urn*='activity']")),
                    "artdeco_card": len(soup2.select(".artdeco-card")),
                }
                
                # Stage 3: After scroll
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(2000)
                html3 = await page.content()
                soup3 = BeautifulSoup(html3, "html.parser")
                stages["stage_3_after_scroll"] = {
                    "feed_shared_update_v2": len(soup3.select(".feed-shared-update-v2")),
                    "occludable_update": len(soup3.select(".occludable-update")),
                    "data_urn_activity": len(soup3.select("[data-urn*='activity']")),
                    "artdeco_card": len(soup3.select(".artdeco-card")),
                }
                
                # Stage 4: After 10 second wait
                await page.wait_for_timeout(10000)
                html4 = await page.content()
                soup4 = BeautifulSoup(html4, "html.parser")
                stages["stage_4_after_10s"] = {
                    "feed_shared_update_v2": len(soup4.select(".feed-shared-update-v2")),
                    "occludable_update": len(soup4.select(".occludable-update")),
                    "data_urn_activity": len(soup4.select("[data-urn*='activity']")),
                    "artdeco_card": len(soup4.select(".artdeco-card")),
                }
                
                return {
                    "status": "success",
                    "activity_url": activity_url,
                    "stages": stages
                }
                
            finally:
                await browser.close()
                
    except Exception as e:
        return {"error": f"Debug timing test failed: {str(e)}"}

@app.get("/scrape/working")
async def working_scrape_test(
    linkedin_url: str = Query(..., description="LinkedIn profile URL"),
    founder_id: str = Query(..., description="Founder ID"),
    start_date: str = Query("2023-01-01", description="Start date YYYY-MM-DD")
):
    """
    Working scraper using the exact same approach as the successful timing test
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
        from dotenv import load_dotenv
        from bs4 import BeautifulSoup
        from datetime import datetime
        
        # Load environment variables
        load_dotenv()
        linkedin_user = os.getenv("LINKEDIN_USER")
        linkedin_pass = os.getenv("LINKEDIN_PASS")
        
        if not linkedin_user or not linkedin_pass:
            return {"error": "LinkedIn credentials not configured"}
        
        # Parse start date
        start_dt = datetime.fromisoformat(start_date)
        
        async with async_playwright() as pw:
            # Detect if running in production
            is_production = bool(os.getenv("RENDER")) or bool(os.getenv("RAILWAY_ENVIRONMENT")) or not os.getenv("HOME", "").startswith("/Users/")
            
            browser = await pw.chromium.launch_persistent_context(
                user_data_dir="/tmp/linkedin_cache",
                headless=is_production,  # Run headless in production
                slow_mo=0 if is_production else 100,
                args=['--no-sandbox', '--disable-dev-shm-usage'],
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = browser.pages[0] if browser.pages else await browser.new_page()
            
            # Apply stealth
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            # Set timeout
            page.set_default_timeout(10000)
            
            try:
                # Login process (same as timing test)
                await page.goto("https://www.linkedin.com/feed", timeout=15000)
                current_url = page.url
                if "login" in current_url:
                    await page.goto("https://www.linkedin.com/login", timeout=15000)
                    await page.fill("#username", linkedin_user)
                    await page.fill("#password", linkedin_pass)
                    await page.click("button[type=submit]")
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                
                # Navigate to activity page (same as timing test)
                activity_url = linkedin_url.rstrip('/') + '/recent-activity/'
                await page.goto(activity_url, timeout=15000)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                # Wait 3 seconds for posts to load (EXACT same as timing test)
                await page.wait_for_timeout(3000)
                
                # Get HTML (same as timing test)
                html = await page.content()
                
                # Parse with BeautifulSoup using the selectors we know work
                soup = BeautifulSoup(html, "html.parser")
                
                # Use the selectors that worked in timing test
                posts = []
                
                # Try feed-shared-update-v2 first (found 5 in timing test)
                feed_updates = soup.select(".feed-shared-update-v2")
                debug_post_info = []
                
                for i, update in enumerate(feed_updates):
                    post_debug = {
                        "post_index": i,
                        "has_time_element": bool(update.find("time")),
                        "time_elements_count": len(update.find_all("time")),
                        "text_preview": update.get_text(" ", strip=True)[:200],
                    }
                    
                    # Check for time elements and their attributes
                    time_elements = update.find_all("time")
                    for j, time_elem in enumerate(time_elements):
                        if hasattr(time_elem, 'attrs') and time_elem.attrs:
                            post_debug[f"time_{j}_attrs"] = dict(time_elem.attrs)
                        else:
                            post_debug[f"time_{j}_attrs"] = "no_attrs"
                    
                    # Check for any datetime-related attributes in the entire update
                    datetime_attrs = []
                    for elem in update.find_all(attrs=True):
                        for attr_name, attr_value in elem.attrs.items():
                            if 'date' in attr_name.lower() or 'time' in attr_name.lower():
                                datetime_attrs.append(f"{attr_name}: {attr_value}")
                    post_debug["datetime_related_attrs"] = datetime_attrs[:5]  # First 5 only
                    
                    debug_post_info.append(post_debug)
                    
                    # Extract post without requiring strict datetime (LinkedIn activity posts don't have <time> elements)
                    # Extract post text
                    post_text = " ".join(update.get_text(" ", strip=True).split())
                    
                    # Skip if post text is too short (likely not a real post)
                    if len(post_text.strip()) < 50:
                        continue
                    
                    # Extract post URL
                    link_elem = update.select_one("a[href*='/feed/update']")
                    post_url = None
                    if link_elem and hasattr(link_elem, 'get'):
                        href = link_elem.get("href")
                        if href and isinstance(href, str):
                            post_url = href.split("?")[0]
                    
                    # Look for relative time indicators in the text
                    relative_time = None
                    post_text_lower = post_text.lower()
                    time_indicators = ["d ago", "day ago", "days ago", "w ago", "week ago", "weeks ago", "m ago", "month ago", "months ago", "y ago", "year ago", "years ago", "h ago", "hour ago", "hours ago"]
                    for indicator in time_indicators:
                        if indicator in post_text_lower:
                            # Find the number before the indicator
                            import re
                            pattern = r'(\d+)\s*' + re.escape(indicator)
                            match = re.search(pattern, post_text_lower)
                            if match:
                                relative_time = match.group(0)
                                break
                    
                    posts.append({
                        "founder_id": founder_id,
                        "post_text": post_text,
                        "post_url": post_url,
                        "posted_at": relative_time or "unknown",  # Use relative time or "unknown"
                        "extraction_method": "activity_page_no_datetime"
                    })
                
                # If no posts from feed-shared-update-v2, try occludable-update
                if not posts:
                    occludable_updates = soup.select(".occludable-update")
                    for i, update in enumerate(occludable_updates):
                        time_elem = update.find("time")
                        if time_elem and hasattr(time_elem, 'attrs') and time_elem.attrs:
                            datetime_attr = time_elem.attrs.get("datetime")
                            if datetime_attr:
                                try:
                                    posted = datetime.fromisoformat(datetime_attr)
                                    if posted >= start_dt:
                                        post_text = " ".join(update.get_text(" ", strip=True).split())
                                        
                                        link_elem = update.select_one("a[href*='/feed/update']")
                                        post_url = None
                                        if link_elem and hasattr(link_elem, 'get'):
                                            href = link_elem.get("href")
                                            if href and isinstance(href, str):
                                                post_url = href.split("?")[0]
                                        
                                        posts.append({
                                            "founder_id": founder_id,
                                            "post_text": post_text,
                                            "post_url": post_url,
                                            "posted_at": posted.isoformat()
                                        })
                                except ValueError:
                                    continue
                
                return {
                    "status": "success",
                    "posts_found": len(posts),
                    "posts": posts,
                    "debug_info": {
                        "activity_url": activity_url,
                        "html_length": len(html),
                        "feed_shared_update_v2_count": len(soup.select(".feed-shared-update-v2")),
                        "occludable_update_count": len(soup.select(".occludable-update")),
                        "data_urn_activity_count": len(soup.select("[data-urn*='activity']")),
                        "artdeco_card_count": len(soup.select(".artdeco-card")),
                        "debug_post_info": debug_post_info
                    }
                }
                
            finally:
                await browser.close()
                
    except Exception as e:
        return {"error": f"Working scraper failed: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
