import ast
import unittest
from pathlib import Path

from recipe_scrapers import get_supported_urls
from recipe_scrapers._abstract import AbstractScraper
from recipe_scrapers._grouping_utils import group_ingredients_jp
from recipe_scrapers._site_recipe_fallback import SiteRecipeFallbackScraper
from recipe_scrapers._utils_jp import get_minutes_jp


JAPANESE_HOSTS = (
    "cookpad.com",
    "kurashiru.com",
    "delishkitchen.tv",
    "recipe.rakuten.co.jp",
    "oceans-nadia.com",
    "macaro-ni.jp",
    "lettuceclub.net",
    "kikkoman.co.jp",
    "dancyu.jp",
)


def targeted_domains():
    source_path = Path("tests/library/test_souschef_targeted_scrapers.py")
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "TARGETED_DOMAINS":
                return ast.literal_eval(node.value)
    raise AssertionError("TARGETED_DOMAINS is missing from the targeted scraper tests")


class TestSouschefForkInvariants(unittest.TestCase):
    def test_japanese_and_targeted_hosts_stay_registered(self):
        supported_urls = get_supported_urls()
        required_hosts = JAPANESE_HOSTS + tuple(targeted_domains())

        for host in required_hosts:
            with self.subTest(host=host):
                self.assertIn(host, supported_urls)

    def test_japanese_grouping_and_fallback_helpers_stay_importable(self):
        self.assertTrue(callable(group_ingredients_jp))
        self.assertTrue(callable(get_minutes_jp))
        self.assertTrue(issubclass(SiteRecipeFallbackScraper, AbstractScraper))

    def test_browser_like_request_headers_stay_in_place(self):
        from recipe_scrapers._abstract import HEADERS

        user_agent = HEADERS.get("user-agent", "")
        self.assertIn("Mozilla/5.0", user_agent)
