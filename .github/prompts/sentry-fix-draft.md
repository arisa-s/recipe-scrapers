Autorun a minimal safe fix PR for this canonical Sentry issue: {{GITHUB_ISSUE_OR_SENTRY_URL}}.

Use the existing canonical issue, investigation notes, duplicate/root-cause decision, and safety plan as the starting point. Fetch fresh Sentry or supporting MCP context only when the existing issue lacks the metadata needed to make a safe fix. Then follow the low-risk AI fix candidate route regardless of risk label: implement the smallest code change that addresses the root cause, add/update a regression test, and make review risk explicit in the PR summary.

This repository is the Souschef fork of hhursev/recipe-scrapers. Flask installs it from `main` and calls `scrape_html` plus `AbstractScraper` methods. Do not change Flask, Rails, or the normalized recipe payload from this repo.

Requirements:
- create or update an open, reviewable PR; do not create it as a draft because Cursor Bugbot may skip draft PRs unless draft reviews are enabled
- clearly mark the PR as requiring human review before merge; never merge, deploy, promote, roll back, pause services, restore databases, run production migrations, or change production config
- preserve existing architecture, Japanese grouping (`group_ingredients_jp`), `SiteRecipeFallbackScraper`, fork-only scrapers, and the browser-like `HEADERS` in `_abstract.py`
- do not rebase onto upstream and do not publish to PyPI
- do not change unrelated behavior
- do not log PII or secrets
- add or update tests that reproduce the observed failure
- run the targeted unittest module, then `python -m unittest tests.library.test_souschef_fork_invariants tests.library.test_flask_consumer_contract tests.library.test_souschef_targeted_scrapers`, then `pre-commit run --files` on the files you changed
- run `unittest-parallel --level test` when practical
- after creating or updating the PR, comment exactly `bugbot run` on the PR to request Cursor Bugbot review
- return the PR URL, files changed, commands run, and remaining risk
