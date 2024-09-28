import re
from typing import List

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup, group_ingredients_jp


class Kurashiru(AbstractScraper):
    @classmethod
    def host(cls):
        return "kurashiru.com"

    def site_name(self):
        return "Kurashiru"

    def title(self):
        title = self.soup.find("h1", class_="title").get_text()
        cleaned_title = re.sub(r"\s*レシピ・作り方$", "", title)
        return cleaned_title

    def ingredient_groups(self) -> List[IngredientGroup]:
        return group_ingredients_jp(self.soup, "ingredient-list-item", "group-title")
