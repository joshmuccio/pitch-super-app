from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Import scraper functionality
from app.scraper import ScrapePayload, scrape_linkedin_posts

# Load environment variables
load_dotenv()

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
    posts: List[Dict[str, Any]]
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
        "endpoints": ["/health", "/embed", "/summarize", "/scrape"]
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

# LinkedIn scraping endpoint (Day 1 implementation)
@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_linkedin(request: ScrapePayload):
    """
    Scrape LinkedIn posts from a founder's profile using Playwright
    Returns posts that can be inserted into Supabase with embedding = NULL
    """
    try:
        posts = await scrape_linkedin_posts(request)
        return {
            "posts": posts,
            "status": "ok"
        }
    except Exception as e:
        return {
            "posts": [],
            "status": f"error: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
