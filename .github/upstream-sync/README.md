# Upstream sync and bug-fix agents

Scheduled workflows run only after this setup is on `main` of `arisa-s/recipe-scrapers`.

## Weekly upstream sync

`.github/workflows/upstream-sync.yml` runs Mondays at 08:00 UTC, and when someone starts it manually. It merge-commits `hhursev/recipe-scrapers` `main` into `sync/upstream` and opens or updates one pull request. It does not rebase and it does not merge to `main`.

Fork-only paths in `ours-paths.yml` keep the Souschef version. `recipe_scrapers/__init__.py` imports and `SCRAPERS` entries are unioned. The same host keeps the fork class. Other dual-owned files use a normal 3-way merge. Leftover conflict markers stay for the Cursor agent.

The pull request comment `Upstream sync report` says whether the merge is safe to merge to `main` for the Flask consumer described in `flask-contract.md`. Merging the pull request to `main` pins that commit in `souschef-flask-server` and redeploys production Flask on Railway.

The job force-updates `sync/upstream` from current `main` plus upstream each run. Conflict fixes that are only on that branch are rebuilt the next week. Merge the pull request, or encode a lasting resolution in `ours-paths.yml` / `upstream_sync.py`.

## Bug-fix agent

`.github/workflows/sentry-cursor-automation.yml` matches the Flask and Rails setup. Scraper errors are reported in the Flask Sentry project. Open an issue from `.github/ISSUE_TEMPLATE/sentry-production-bug.md` with the Sentry URL, or comment `/sentry-all` on an issue labeled `sentry`.

The agent may open a non-draft pull request. It must not merge or deploy. Comment `bugbot run` requests Cursor Bugbot.

## Repository secrets

- `CURSOR_API_KEY` — Cursor agent for the sync report, bug-fix flow, and `add-site.yml`
- `SENTRY_ACCESS_TOKEN` — Sentry REST API and Sentry MCP for the bug-fix flow
- `SYNC_GITHUB_TOKEN` or `SENTRY_CURSOR_GITHUB_TOKEN` — push `sync/upstream` and open pull requests when `GITHUB_TOKEN` cannot
- `FLASK_DEPLOY_KEY` — private half of a write deploy key on `arisa-s/souschef-flask-server`. `deploy-flask.yml` uses it to push the scraper pin that Railway builds
- `SLACK_BOT_TOKEN` — Slack bot token with `chat:write` and `pins:write`. Invite the bot to the channel below. `pin-site-pr.yml` posts and pins a message when a pull request is opened from a `site/` branch. Later pushes to that pull request are not pinned again.

## Add a website from Slack

`add-site.yml` can be started from the Actions tab, or from Slack. In Slack, type:

```
/add-site https://example.com/recipes/pasta
Ingredients are only in the method, not a list.
```

The URL is required. The note is optional. If the URL is missing, Slack replies with that template and does not start a run. The slash command posts to Rails `POST /webhooks/slack/add_site`. Rails needs `SLACK_SIGNING_SECRET`, `SLACK_CHANNEL_ID`, and `RECIPE_SCRAPERS_DISPATCH_TOKEN` (a GitHub token that can dispatch this workflow). When `add-site.yml` finishes, it pins the result in Slack, including the pull request link when one was opened. `pin-site-pr.yml` also pins when any pull request is opened from a `site/` branch.

## Repository variables

- `SLACK_CHANNEL_ID` — channel that receives the pinned new-website pull request, and the only channel that may run `/add-site`, for example `C0123456789`
- `SLACK_BOT_TOKEN` — Slack bot token with `chat:write` and `pins:write`. Invite the bot to the channel below. When the weekly job opens a new sync pull request, it posts the link and pins that message. Updating an existing sync pull request does not pin again.

## Repository variables

- `SLACK_CHANNEL_ID` — channel that receives the pinned sync pull request, for example `C0123456789`
- `CURSOR_MODEL` — model for investigation and the sync report; defaults to `auto`
- `CURSOR_FIX_MODEL` — model for fix pull requests; falls back to `CURSOR_MODEL`
- `SENTRY_BASE_URL` — optional, defaults to `https://sentry.io`
- `PUBLISH_TO_PYPI` — leave unset. The string `true` is required before `publish.yaml` can upload a release, and this fork must not publish the public `recipe-scrapers` package

## Labels

Create the labels in `.github/labels.yml` before using the issue template. `merge-guards.yml` blocks a pull request while it has the `needs-tests` label.
