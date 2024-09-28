from ._abstract import AbstractScraper
from ._grouping_utils import group_ingredients_jp


class RakutenRecipe(AbstractScraper):
    @classmethod
    def host(cls):
        return "recipe.rakuten.co.jp"

    def site_name(self):
        return "Rakuten Recipe"

    def ingredient_groups(self):
        return group_ingredients_jp(
            self.soup,
            "recipe_material__list",
            None,
            None,
            "recipe_material__item_serving",
        )
