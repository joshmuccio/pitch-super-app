-- ---------- EXTENSIONS ----------
create extension if not exists "uuid-ossp";
create extension if not exists vector with schema public;  -- pgvector in `public`

-- ---------- TABLES ----------
create table if not exists founders (
  id           uuid primary key default uuid_generate_v4(),
  full_name    text not null,
  linkedin_url text unique not null,
  company_id   uuid
);

create table if not exists linkedin_posts (
  id          uuid primary key default uuid_generate_v4(),
  founder_id  uuid references founders(id) on delete cascade,
  post_text   text not null,
  post_url    text,
  posted_at   timestamptz,
  scraped_at  timestamptz default now(),
  embedding   vector(1536),                    -- stays 1536-dim
  constraint  unique_post unique(founder_id, post_url)
);

create table if not exists weekly_summaries (
  id          uuid primary key default uuid_generate_v4(),
  company_id  uuid,
  model_name  text,
  summary_md  text,
  created_at  timestamptz default now()
);

-- ---------- INDEXES ----------
create index if not exists idx_linkedin_posts_embedding
  on linkedin_posts using hnsw (embedding vector_cosine_ops);

create index if not exists idx_linkedin_posts_founder_posted_at
  on linkedin_posts(founder_id, posted_at);

create index if not exists idx_weekly_summaries_company_created
  on weekly_summaries(company_id, created_at); 