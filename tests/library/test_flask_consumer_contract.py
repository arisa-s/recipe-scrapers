import dataclasses
import inspect
import unittest

from recipe_scrapers import scrape_html
from recipe_scrapers._abstract import AbstractScraper
from recipe_scrapers._exceptions import (
    NoSchemaFoundInWildMode,
    WebsiteNotImplementedError,
)
from recipe_scrapers._grouping_utils import IngredientGroup


FLASK_METHODS = (
    "title",
    "ingredient_groups",
    "ingredients",
    "instructions",
    "instructions_list",
    "host",
    "image",
    "prep_time",
    "cook_time",
    "total_time",
    "yields",
    "nutrients",
    "author",
    "cuisine",
    "dietary_restrictions",
    "category",
    "keywords",
)


class TestFlaskConsumerContract(unittest.TestCase):
    def test_scrape_html_accepts_flask_arguments(self):
        parameters = inspect.signature(scrape_html).parameters

        self.assertIn("html", parameters)
        self.assertIn("org_url", parameters)
        self.assertIn("supported_only", parameters)

    def test_supported_only_still_selects_wild_mode(self):
        with self.assertRaises(WebsiteNotImplementedError):
            scrape_html(
                "<html></html>",
                "https://example.com/recipe",
                supported_only=True,
            )

        with self.assertRaises(NoSchemaFoundInWildMode):
            scrape_html(
                "<html><body>no recipe</body></html>",
                "https://example.com/recipe",
                supported_only=False,
            )

    def test_private_wild_mode_exception_stays_importable(self):
        self.assertTrue(issubclass(NoSchemaFoundInWildMode, Exception))

    def test_abstract_scraper_keeps_flask_methods(self):
        for name in FLASK_METHODS:
            with self.subTest(method=name):
                self.assertTrue(callable(getattr(AbstractScraper, name)))

    def test_ingredient_group_keeps_flask_fields(self):
        group = IngredientGroup(ingredients=["1 onion"], purpose="sauce")
        fields = {field.name for field in dataclasses.fields(IngredientGroup)}

        self.assertEqual(group.ingredients, ["1 onion"])
        self.assertEqual(group.purpose, "sauce")
        self.assertIn("ingredients", fields)
        self.assertIn("purpose", fields)
