Decide whether this Sentry issue is a duplicate/root-cause match for existing GitHub or Sentry issues: {{SENTRY_URL_OR_ID}}.

Do not edit files. Do not use Seer. Use Sentry MCP to compare recent events, tag distributions, releases, request/trace IDs, error_key, feature, endpoint/job, source_domain, and top application stack frames across Expo, Rails, and Flask. Search local repo context only as needed to understand ownership, including `arisa:recipe-scrapers` for web import/parser failures.

If relevant and configured, use supporting MCPs read-only to compare deploy/runtime context:
- Railway MCP for backend/flask deploys, logs, Redis, and Sidekiq symptoms.
- Expo MCP for frontend build/update/channel context.
- Supabase MCP for auth/database/realtime/storage logs and advisor signals.

Return:
- canonical root-cause key proposal
- matching existing Sentry issues, if any
- matching GitHub issues/PRs, if any
- evidence for duplicate vs separate issue
- recommended canonical owner service
- whether ownership should be `recipe-scrapers` even though it has no direct Sentry project
- labels to add
- whether to create a new GitHub issue or comment on an existing one
