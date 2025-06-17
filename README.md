# Pitch Super App

Internal data + AI platform for The Pitch Fund.

## Architecture

- **Backend**: FastAPI + LangChain for AI-powered content analysis
- **Database**: Supabase (PostgreSQL + pgvector)
- **Automation**: n8n workflows for scraping and digestion
- **AI Models**: OpenAI embeddings + multiple LLMs for summarization
- **Deployment**: Render (backend), Vercel (frontend)

## Project Structure

```
pitch-super-app/
├─ backend/              # FastAPI micro-service
│   ├─ app/              # Python source
│   ├─ tests/            # Unit tests
│   ├─ requirements.txt  # Dependencies
│   └─ Dockerfile        # Container config
├─ workflows/            # n8n export JSON files
├─ supabase/             # Database schema & migrations
├─ frontend/             # Next.js UI (future)
├─ docs/                 # Documentation
├─ .env.example          # Environment template
└─ .gitignore
```

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
   uvicorn app.main:app --reload
   ```

4. **n8n Workflows**
   - Import `workflows/*.json` files into your n8n instance
   - Configure with your credentials

## Environment Variables

See `.env.example` for required configuration variables.

## Deployment

- **Backend**: Deploy to Render using the included Dockerfile
- **Workflows**: Set up n8n Cloud with imported workflow files
- **Database**: Supabase hosted PostgreSQL

## Development Timeline

- **Day 1**: LinkedIn backfill scraping
- **Day 2**: Embedding pipeline
- **Day 3**: Summarization endpoints
- **Day 4**: Weekly digest automation
- **Day 5**: Monitoring & documentation