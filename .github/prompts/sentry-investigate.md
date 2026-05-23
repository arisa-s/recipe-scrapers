Investigate this Sentry issue without editing files or creating a branch: {{SENTRY_URL_OR_ID}}.

Use Sentry MCP as the primary source. Do not use Seer. Inspect correlated events across the Expo, Rails, and Flask Sentry projects. Then inspect local repo code as needed, including `arisa:recipe-scrapers` when the issue is a web recipe import or site-specific extraction failure.

If relevant and configured, also use supporting MCPs in read-only mode:
- Railway MCP for Rails, Redis, Sidekiq, and Flask deployment status/log/runtime context.
- Expo MCP for app build, release/channel, runtime version, EAS update, and native deployment context.
- Supabase MCP for Auth, Postgres, Storage, Realtime, advisors, and recent service logs.

Do not run write/deploy/migration/restore/pause/configuration-changing actions through any MCP during investigation.

Return:
- affected project(s) and likely canonical owner service
- exception summary and top application stack frames
- relevant tags: request_id, upstream_request_id, trace_id, user_id, release, feature, error_key, source_domain/source_url, endpoint/controller/action/job_name
- relevant Railway/Expo/Supabase context, if checked
- whether related frontend/backend/flask issues appear to be the same incident
- likely root cause and confidence level
- risk label: low, medium, or high
- files likely involved
- whether `arisa:recipe-scrapers` is the likely root-cause repo
- minimum regression test plan
- whether an AI draft PR is safe, and why
