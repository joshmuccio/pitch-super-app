# Pitch Super App Plan

## Day 0 – Setup (30 min)
- Sign up: [n8n Cloud](https://n8n.io/), [Supabase](https://supabase.com/), [Render](https://render.com/), [Vercel](https://vercel.com/), [Slack](https://slack.com/).
- Create GitHub repo: `pitch-super-app`.
- Add `.env.example` with the variables shown at the end.

---

## Day 1 – Backfill Historical Posts

1️⃣ Run SQL above.

2️⃣ In n8n create workflow **"LinkedIn Backfill"**:
- **Set node**: `start_date = 2023-01-01`.
- **Items node**: list founder profile URLs.
- **Function node (Puppeteer)**:  
  - Logs in with your credentials  
  - Scrolls until it hits `start_date`  
  - Extracts plain text + URL + `posted_at`  
  - Use `page.waitForNetworkIdle()` after each scroll
- **Supabase node**: bulk-inserts rows (`embedding = NULL`)

---

## Day 2 – Embedding Pipeline

- Deploy **FastAPI** on Render with `/embed` endpoint:
  - Strips HTML
  - Chunks text
  - Calls OpenAI embeddings
  - Returns vectors

- **Nightly n8n cron**:
  - Select rows where `embedding IS NULL`
  - Hit `/embed`
  - Update the column

---

## Day 3 – `/summarize` Endpoint

Inside **FastAPI** (LangChain):

1. Select this week’s posts for a company  
2. For every chunk, query `pgvector` for top-K neighbours (cosine distance)  
3. Deduplicate chunks  
4. Run LangChain Map-Reduce chain once per model in `[gpt-4o, gpt-3.5-turbo, claude-3-sonnet]`  
5. Return JSON:  
   ```json
   {
     "model_name": "summary_md"
   }
   
---

## Day 4 – Weekly Digest Job

- **n8n cron job**: Every Friday at 07:00 ET  
  → Loop through companies  
  → Call `/summarize` endpoint  
  → Upsert results into `weekly_summaries` table

- **Supabase Edge Function**: `send_weekly_update`
  - Builds a Markdown digest grouped by company and model
  - Sends the digest via SMTP email

---

## Day 5 – Monitoring & Docs

- **Monitoring**
  - Use n8n's global Error Trigger → Send email notification to you
  - Add a `/health` route to FastAPI app
  - Set up Render Cron job:
    - Nightly `curl /health`
    - If response is not 200, trigger a Slack webhook alert

- **Documentation**
  - Write a `README.md` including:
    - Required environment variables
    - n8n workflow URLs
    - Deployment steps for each service
    - A link to this setup plan