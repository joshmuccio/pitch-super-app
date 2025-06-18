from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Import scraper functionality
from app.scraper import ScrapePayload, scrape_linkedin_posts

# Import Supabase client
from supabase import create_client

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")   # service role!
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

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

@app.post("/scrape/debug")
async def scrape_linkedin_debug(request: ScrapePayload):
    """
    DEBUG version of scraper - returns detailed logs instead of writing to DB
    """
    try:
        # Capture debug output
        import sys
        from io import StringIO
        
        # Redirect stdout to capture debug prints
        old_stdout = sys.stdout
        debug_output = StringIO()
        sys.stdout = debug_output
        
        try:
            posts = await scrape_linkedin_posts(request)
        finally:
            sys.stdout = old_stdout
        
        debug_logs = debug_output.getvalue()
        
        return {
            "posts_found": len(posts) if posts and not ("error" in str(posts)) else 0,
            "posts": posts[:3] if posts else [],  # Return first 3 posts for preview
            "debug_logs": debug_logs,
            "status": "debug_complete"
        }
        
    except Exception as e:
        return {
            "posts_found": 0,
            "posts": [],
            "debug_logs": f"Error: {str(e)}",
            "status": f"debug_error: {str(e)}"
        }

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_linkedin(request: ScrapePayload):
    """
    Scrape LinkedIn posts from a founder's profile using Playwright
    Writes posts directly to Supabase and returns insertion count
    """
    try:
        # Scrape posts from LinkedIn
        posts = await scrape_linkedin_posts(request)
        
        # Handle scraper errors (from timeout optimization)
        if posts and isinstance(posts[0], dict) and "error" in posts[0]:
            return {
                "inserted": 0,
                "status": f"scraper_error: {posts[0]['error']}"
            }
        
        # Insert posts directly into Supabase
        if posts:
            result = sb.table("linkedin_posts").upsert(posts).execute()
            return {
                "inserted": len(posts),
                "status": "ok"
            }
        else:
            return {
                "inserted": 0,
                "status": "no_posts_found"
            }
            
    except Exception as e:
        return {
            "inserted": 0,
            "status": f"error: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
