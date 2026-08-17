# Build order

1. ✅ DB schema (`app/database.py`, `app/models.py`, `app/schemas.py`)
2. `alembic init` + first migration to push schema to Neon
3. GitHub OAuth + JWT (`app/auth.py`) — reuse Distill's OAuth flow, swap callback URL
4. `app/routes/problems.py` — POST create, GET feed w/ category+domain filter, DELETE (poster-only)
5. `app/routes/verification.py` — upload ID photo to Supabase, POST submit, admin-only PATCH review
6. `app/routes/claims.py` — POST claim (checks `is_verified_solver`), POST unclaim, cron/check for 30-day auto-reopen
7. `app/routes/solutions.py` — POST github_repo_url + is_public → sets problem.status = solved
8. `app/routes/comments.py` — POST comment (run through better-profanity filter → is_flagged), GET thread
9. `app/routes/reports.py` — POST report (problem or comment), GET pending queue (admin-only)
10. Frontend: plain HTML/JS pages — feed, post form, problem detail, my-claims, admin review queue
11. Deploy: Render (backend) + Vercel (frontend) + Neon (already have this from Distill)

## Notes / decisions baked into the schema
- `Claim` keeps full history (not overwritten) so unclaim → reclaim is auditable. Only one `in_progress`
  claim per problem should exist at a time — enforce in route logic, not a DB constraint.
- `valid_until` defaults to +4 years on approval but is admin-adjustable per the spec.
- `is_public` on the solution gates repo link visibility — check in the GET problem route, not just frontend.
- 30-day auto-reopen: cheapest v1 approach is a simple cron script (`scripts/reopen_stale_claims.py`) run
  daily via Render's cron job feature (free tier has this) rather than APScheduler in-process — keeps it
  stateless and restart-safe.
