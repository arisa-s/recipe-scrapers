Verify the deployed fix for this canonical Sentry issue: {{GITHUB_ISSUE_OR_SENTRY_URL}}.

Use Sentry MCP as the primary source. Do not use Seer. Search production events scoped by the canonical Sentry issue, related issue IDs, release, environment, root-cause key, request/trace metadata, feature, error_key, and source_domain.

If relevant and configured, use supporting MCPs read-only:
- Railway MCP for deploy status, logs, service metrics, HTTP errors, Redis, and Sidekiq symptoms.
- Expo MCP for build/update/channel/runtime version context.
- Supabase MCP for Auth, database, storage, realtime logs, and advisor signals.

Do not merge, deploy, roll back, pause services, restore databases, run migrations, or change production config.

Return:
- verification status: verified | still-failing | inconclusive
- Sentry queries run
- releases/environments checked
- new matching events, if any
- Railway/Expo/Supabase context checked, if any
- recommended next action
