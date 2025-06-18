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

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")   # service role!

# Only initialize Supabase if we have valid credentials
sb = None
if SUPABASE_URL and SUPABASE_KEY and not SUPABASE_URL.startswith("your_"):
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized")
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
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "pitch-super-app-api"}

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
                    # Create embedding for the post
                    embedding = await create_embedding(post["post_text"])
                    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
