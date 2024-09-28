from typing import List

from recipe_scrapers._grouping_utils import group_ingredients_jp

from ._abstract import AbstractScraper


class DelishKitchen(AbstractScraper):
    @classmethod
    def host(cls):
        return "delishkitchen.tv"

    def site_name(self):
        return "Delish Kitchen"

    def ingredient_groups(self):
        return group_ingredients_jp(
            self.soup,
            "ingredient-list",
            "ingredient-group__header",
            None,
            "ingredient-serving",
        )
