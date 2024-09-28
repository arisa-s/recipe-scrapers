from typing import List

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup, group_ingredients_jp


class CookPad(AbstractScraper):
    @classmethod
    def host(cls):
        return "cookpad.com"

    def site_name(self):
        return "Cookpad"

    def ingredient_groups(self) -> List[IngredientGroup]:
        return group_ingredients_jp(
            self.soup, "justified-quantity-and-name", "headline"
        )
