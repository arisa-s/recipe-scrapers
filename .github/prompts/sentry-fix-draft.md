Autorun a minimal safe draft fix for this canonical Sentry issue: {{GITHUB_ISSUE_OR_SENTRY_URL}}.

Use the existing canonical issue, investigation notes, duplicate/root-cause decision, and safety plan as the starting point. Fetch fresh Sentry or supporting MCP context only when the existing issue lacks the metadata needed to make a safe fix. Then follow the low-risk AI fix candidate route regardless of risk label: implement the smallest code change that addresses the root cause, add/update a regression test, and make review risk explicit in the PR summary.

Requirements:
- create or update a draft PR only; never merge, deploy, promote, roll back, pause services, restore databases, run production migrations, or change production config
- preserve existing architecture and service boundaries
- if root cause is in `arisa:recipe-scrapers`, create the draft PR in that repo and add/update fixture-based scraper tests for the affected domain
- do not change unrelated behavior
- do not log PII or secrets
- do not use Railway/Expo/Supabase MCP write/deploy/migration/restore/pause/configuration-changing actions
- add or update tests that reproduce the observed failure
- run the targeted test command, then the repo safety gate command where practical
- return the draft PR URL, files changed, commands run, remaining risk, and Sentry verification query for after deploy
