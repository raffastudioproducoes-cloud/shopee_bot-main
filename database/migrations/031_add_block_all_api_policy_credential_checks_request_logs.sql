-- Applied to production (Supabase: autovendas) on 2026-09-29 via Supabase MCP

create policy "block_all_api" on public.credential_checks for all using (false) with check (false);
create policy "block_all_api" on public.request_logs for all using (false) with check (false);
