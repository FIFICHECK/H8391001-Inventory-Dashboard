-- ═══════════════════════════════════════════════════════════════
-- H8391001 Dashboard — Email Access Gate (access_requests + access_approved)
-- Run this in Supabase SQL Editor (https://supabase.com/dashboard → SQL Editor)
-- Project: mbeftbvpeqfmyxvbpmcy (same as todo-dashboard-supabase)
-- ═══════════════════════════════════════════════════════════════

-- 1. access_requests: 訪客提交嘅申請 (visitor submits email → row created)
create table if not exists public.access_requests (
  id bigint generated always as identity primary key,
  email text not null,
  status text not null default 'pending',        -- pending / approved / denied
  created_at timestamptz not null default now(),
  notified_at timestamptz,                        -- 通知咗 Jerry 未 (Hermes 寫)
  decided_at timestamptz                          -- approve/deny 時間
);

-- 2. access_approved: 已批准 email allowlist (Hermes 寫, 訪客讀)
create table if not exists public.access_approved (
  email text primary key,
  approved_at timestamptz not null default now()
);

-- RLS (POC permissive — 同 todo-dashboard 一致:
-- anon key 係公開嘅，保護靠 approve workflow 而唔係 RLS)
alter table public.access_requests enable row level security;
alter table public.access_approved enable row level security;

drop policy if exists "poc full access" on public.access_requests;
drop policy if exists "poc full access" on public.access_approved;

create policy "poc full access" on public.access_requests
  for all using (true) with check (true);

create policy "poc full access" on public.access_approved
  for all using (true) with check (true);
