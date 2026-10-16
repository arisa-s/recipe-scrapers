Investigate this Sentry issue without editing files or creating a branch: {{SENTRY_URL_OR_ID}}.

Scraper failures are reported in the Flask Sentry project. Use Sentry MCP as the primary source. Inspect the Flask event and this recipe-scrapers fork. Only use cross-project correlation metadata already present on the event.

Do not run write/deploy/migration/restore/pause/configuration-changing actions through any MCP during investigation.

Return:
- whether the canonical owner is recipe-scrapers or Flask
- exception summary and top application stack frames
- relevant tags: request_id, upstream_request_id, trace_id, user_id, release, feature, error_key, scrape_source, source_url
- likely root cause and confidence level
- risk label: low, medium, or high
- files likely involved in this fork
- minimum regression test plan, using a unittest fixture under tests/test_data or tests/fixtures/souschef_targeted
- whether an AI fix PR is safe, and why
