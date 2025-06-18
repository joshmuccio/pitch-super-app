# Pitch Super App

Internal data + AI platform for The Pitch Fund.

## Architecture

- **Backend**: FastAPI + LangChain for AI-powered content analysis  
- **Scraping**: Hybrid approach - n8n workflows OR direct Playwright scraper service
- **Database**: Supabase (PostgreSQL + pgvector)
- **AI Models**: OpenAI embeddings + multiple LLMs for summarization
- **Deployment**: Render (backend), Vercel (frontend)

## Database Schema

```sql
-- Core entities
companies (id, name, website, headquarters, linkedin_url)
founders (id, full_name, linkedin_url, company_id → companies)

-- Content & Analysis  
linkedin_posts (id, founder_id → founders, company_id → companies, 
                post_text, post_url, posted_at, scraped_at, embedding[1536])
weekly_summaries (id, company_id → companies, model_name, summary_md, created_at)

-- Key constraints
UNIQUE (coalesce(founder_id, company_id), post_url)  -- Deduplication
```

**Relationships:**
- Companies can have many founders and posts
- Posts can be linked to either founders OR companies directly  
- Unique constraint prevents duplicate posts per entity
- 1536-dim embeddings for semantic search

## Project Structure

```
pitch-super-app/
├─ backend/              # FastAPI micro-service
│   ├─ app/              # Python source
│   │   ├─ main.py       # FastAPI app with all endpoints
│   │   ├─ embed.py      # OpenAI embedding functions
│   │   └─ scraper.py    # LinkedIn scraper service
│   ├─ tests/            # Unit tests
│   ├─ requirements.txt  # Dependencies (FastAPI + Playwright + OpenAI)
│   └─ Dockerfile        # Container config with Playwright support
├─ workflows/            # n8n export JSON files
├─ supabase/             # Database schema & migrations
├─ frontend/             # Next.js UI (future)
├─ docs/                 # Documentation
├─ .env.example          # Environment template
└─ .gitignore
```

## API Endpoints

- **`GET /health`** - Health check endpoint
- **`GET /`** - API information and endpoint list
- **`POST /embed`** - Generate embeddings for text (Day 2)
- **`POST /summarize`** - Multi-model summarization (Day 3)
- **`POST /scrape`** - LinkedIn profile scraping (Day 1)

## Quick Start

1. **Clone & Setup**
   ```bash
   git clone <repo-url>
   cd pitch-super-app
   cp .env.example .env
   # Fill in your actual credentials in .env
   ```

2. **Database Setup**
   - Run `supabase/schema.sql` in your Supabase SQL Editor

3. **Backend Development**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   playwright install chromium
   uvicorn app.main:app --reload
   ```

4. **n8n Workflows (Optional)**
   - Import `workflows/*.json` files into your n8n instance
   - Configure with your credentials

## Scraping Options

### Option 1: Direct API (Recommended)
Use the `/scrape` endpoint directly:
```json
{
  "linkedin_url": "https://linkedin.com/in/founder-profile",
  "founder_id": "uuid-here",
  "start_date": "2024-01-01"
}
```

### Option 2: n8n Workflow
Use the LinkedIn Backfill workflow for automated batch processing.

## Environment Variables

See `.env.example` for all required configuration variables including:
- Supabase database credentials
- OpenAI API key
- LinkedIn credentials for scraping
- n8n webhook URLs
- SMTP settings for digests

## Dependencies

- **FastAPI + Uvicorn** - Web framework
- **Playwright + BeautifulSoup** - Web scraping
- **OpenAI + LangChain** - AI/ML processing
- **Supabase + pgvector** - Database & vector search
- **Python-dotenv** - Environment management

## Deployment

- **Backend**: Deploy to Render using the included Dockerfile
- **Workflows**: Set up n8n Cloud with imported workflow files (optional)
- **Database**: Supabase hosted PostgreSQL

## Development Timeline

- **Day 1**: LinkedIn backfill scraping ✅
- **Day 2**: Embedding pipeline (in progress)
- **Day 3**: Summarization endpoints (in progress)
- **Day 4**: Weekly digest automation
- **Day 5**: Monitoring & documentation