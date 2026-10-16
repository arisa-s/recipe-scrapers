# Upstream sync and bug-fix agents

Scheduled workflows run only after this setup is on `main` of `arisa-s/recipe-scrapers`.

## Weekly upstream sync

`.github/workflows/upstream-sync.yml` runs Mondays at 08:00 UTC, and when someone starts it manually. It merge-commits `hhursev/recipe-scrapers` `main` into `sync/upstream` and opens or updates one pull request. It does not rebase and it does not merge to `main`.

Fork-only paths in `ours-paths.yml` keep the Souschef version. `recipe_scrapers/__init__.py` imports and `SCRAPERS` entries are unioned. The same host keeps the fork class. Other dual-owned files use a normal 3-way merge. Leftover conflict markers stay for the Cursor agent.

The pull request comment `Upstream sync report` says whether the merge is safe to merge to `main` for the Flask consumer described in `flask-contract.md`. Flask installs this repo from `main`, so merging the pull request changes the next Flask rebuild.

The job force-updates `sync/upstream` from current `main` plus upstream each run. Conflict fixes that are only on that branch are rebuilt the next week. Merge the pull request, or encode a lasting resolution in `ours-paths.yml` / `upstream_sync.py`.

## Bug-fix agent

`.github/workflows/sentry-cursor-automation.yml` matches the Flask and Rails setup. Scraper errors are reported in the Flask Sentry project. Open an issue from `.github/ISSUE_TEMPLATE/sentry-production-bug.md` with the Sentry URL, or comment `/sentry-all` on an issue labeled `sentry`.

The agent may open a non-draft pull request. It must not merge or deploy. Comment `bugbot run` requests Cursor Bugbot.

## Repository secrets

- `CURSOR_API_KEY` — Cursor agent for the sync report and bug-fix flow
- `SENTRY_ACCESS_TOKEN` — Sentry REST API and Sentry MCP for the bug-fix flow
- `SYNC_GITHUB_TOKEN` or `SENTRY_CURSOR_GITHUB_TOKEN` — push `sync/upstream` and open pull requests when `GITHUB_TOKEN` cannot

## Repository variables

- `CURSOR_MODEL` — model for investigation and the sync report; defaults to `auto`
- `CURSOR_FIX_MODEL` — model for fix pull requests; falls back to `CURSOR_MODEL`
- `SENTRY_BASE_URL` — optional, defaults to `https://sentry.io`
- `PUBLISH_TO_PYPI` — leave unset. The string `true` is required before `publish.yaml` can upload a release, and this fork must not publish the public `recipe-scrapers` package

## Labels

Create the labels in `.github/labels.yml` before using the issue template. `merge-guards.yml` blocks a pull request while it has the `needs-tests` label.
