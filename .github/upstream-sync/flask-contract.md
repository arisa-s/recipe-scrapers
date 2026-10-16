# Flask consumer contract

`souschef-flask-server` installs one pinned commit of this fork:

```
git+https://github.com/arisa-s/recipe-scrapers.git@<commit>#egg=recipe_scrapers
```

`.github/workflows/deploy-flask.yml` updates that pin on every push to `main` and pushes `souschef-flask-server` `main`. Railway rebuilds production Flask from that branch.

The web importer in `app/services/recipe_scraper/web/scrape_web_service.py` is the consumer. A weekly sync is safe to merge to `main` only when this surface still behaves the same way.

## Imports

- `from recipe_scrapers import scrape_html`
- `from recipe_scrapers._exceptions import NoSchemaFoundInWildMode`

## Call

`scrape_html(html, org_url, supported_only=False)`

Flask passes the HTML it already fetched. `supported_only=False` is wild mode: known hosts use `SCRAPERS`, unknown hosts use schema.org, and a missing schema raises `NoSchemaFoundInWildMode`.

## Methods

`title`, `ingredient_groups`, `ingredients`, `instructions`, `instructions_list`, `host`, `image`, `prep_time`, `cook_time`, `total_time`, `yields`, `nutrients`, `author`, `cuisine`, `dietary_restrictions`, `category`, `keywords`.

`ingredient_groups()` returns objects with `.purpose` and `.ingredients`. Flask catches `ValueError` from that method and falls back to `ingredients()`.

## Fork behavior Flask relies on

- Japanese hosts stay registered, including `cookpad.com`, `kurashiru.com`, `delishkitchen.tv`, `recipe.rakuten.co.jp`, `oceans-nadia.com`, `macaro-ni.jp`, `lettuceclub.net`, `kikkoman.co.jp`, and `dancyu.jp`.
- `group_ingredients_jp` still groups ingredients for those sites.
- `SiteRecipeFallbackScraper` still covers the targeted domains in `tests/library/test_souschef_targeted_scrapers.py`.
- `_abstract.HEADERS` still sends a browser-like User-Agent.
