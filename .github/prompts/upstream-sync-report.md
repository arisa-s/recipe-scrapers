Review the weekly upstream merge of hhursev/recipe-scrapers into this Souschef fork.

Draft report:
{{REPORT_MARKDOWN}}

Pull request: {{PR_URL}}
Minimum verdict: {{MINIMUM_VERDICT}}
Block reasons: {{BLOCK_REASONS}}

The merge commit is already on branch `sync/upstream`. Do not redo the merge, do not rebase, and do not merge the pull request.

You may edit only files listed in unresolved conflict markers. While doing that:
- keep fork-only files listed in `.github/upstream-sync/ours-paths.yml`
- keep `group_ingredients_jp`, Japanese hosts, and `SiteRecipeFallbackScraper`
- keep the browser-like `HEADERS` user agent in `recipe_scrapers/_abstract.py` when that file conflicts
- keep the fork class when `SCRAPERS` maps one host to two classes
- do not replace `scrape_html`, `NoSchemaFoundInWildMode`, `IngredientGroup.purpose`, or `IngredientGroup.ingredients` with a weaker contract

If you edit files, commit on `sync/upstream`, push that branch, and rerun:
`python -m unittest tests.library.test_souschef_fork_invariants tests.library.test_flask_consumer_contract tests.library.test_souschef_targeted_scrapers`

You may raise the verdict from SAFE to REVIEW or BLOCK. You may clear "unresolved conflict markers" or "unittest failed" only after those problems are actually gone. You may not clear "preservation checks failed" or "__init__.py union failed".

Post one pull request comment that starts with `## Upstream sync report` and includes the final verdict, whether it is safe to merge to `main`, the upstream range, fork-only paths, Flask contract changes, and test results. Merging to `main` pins that commit in `souschef-flask-server` and redeploys production Flask.

Then comment exactly `bugbot run`.

Do not merge, deploy, or push to `main`.
