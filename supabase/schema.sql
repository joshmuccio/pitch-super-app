-- ---------- EXTENSIONS ----------
create extension if not exists "uuid-ossp";
create extension if not exists vector with schema public;  -- pgvector in `public`

-- ---------- TABLES ----------

-- New companies table
create table if not exists companies (
  id           uuid primary key default uuid_generate_v4(),
  name         text unique not null,
  website      text,
  headquarters text,
  linkedin_url text
);

create table if not exists founders (
  id           uuid primary key default uuid_generate_v4(),
  full_name    text not null,
  linkedin_url text unique not null,
  company_id   uuid references companies(id)
);

create table if not exists linkedin_posts (
  id          uuid primary key default uuid_generate_v4(),
  founder_id  uuid references founders(id) on delete cascade,
  company_id  uuid references companies(id),
  post_text   text not null,
  post_url    text,
  posted_at   timestamptz,
  scraped_at  timestamptz default now(),
  embedding   vector(1536)                     -- stays 1536-dim
);

create table if not exists weekly_summaries (
  id          uuid primary key default uuid_generate_v4(),
  company_id  uuid references companies(id),
  model_name  text,
  summary_md  text,
  created_at  timestamptz default now()
);

-- ---------- INDEXES ----------

-- Expression-based UNIQUE index for deduplication (works with NULLs)
create unique index if not exists unique_post
  on linkedin_posts (
    coalesce(founder_id, company_id),
    post_url
  );

create index if not exists idx_linkedin_posts_embedding
  on linkedin_posts using hnsw (embedding vector_cosine_ops);

create index if not exists idx_linkedin_posts_founder_posted_at
  on linkedin_posts(founder_id, posted_at);

create index if not exists idx_linkedin_posts_company_posted_at
  on linkedin_posts(company_id, posted_at);

create index if not exists idx_weekly_summaries_company_created
  on weekly_summaries(company_id, created_at);

create index if not exists idx_founders_company
  on founders(company_id); 