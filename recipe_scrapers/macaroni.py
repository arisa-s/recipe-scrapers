from typing import Dict, Optional

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup, group_ingredients_by_starting_char
from ._utils import normalize_string


class Macaroni(AbstractScraper):
    @classmethod
    def host(cls):
        return "macaro-ni.jp"

    def site_name(self):
        return "Macaroni"

    def ingredient_groups(self):
        group_containers = self.soup.find(
            "li", class_="articleShow__contentsMateriialItem--groupWrapper"
        )

        if group_containers is None:
            return group_ingredients_by_starting_char(self.ingredients(), "ja")

        group_dict: Dict[Optional[str], IngredientGroup] = {
            None: IngredientGroup(ingredients=[], purpose=None)
        }

        ingredients_container = self.soup.find(
            "ul", class_="articleShow__contentsMaterialItems"
        )

        for group_container in ingredients_container.find_all("li", recursive=False):
            if (
                "articleShow__contentsMateriialItem--groupWrapper"
                in group_container.get("class")
            ):
                purpose = normalize_string(
                    group_container.find(
                        "span", class_="articleShow__contentsMaterialName--strong"
                    ).text
                )
                ingredients = group_container.find_all(
                    "li", class_="articleShow__contentsMateriialItem"
                )
                group_dict[purpose] = IngredientGroup(
                    ingredients=[
                        normalize_string(ingredient_tag.text)
                        for ingredient_tag in ingredients
                    ],
                    purpose=purpose,
                )
            else:
                group_dict[None].ingredients.append(
                    normalize_string(group_container.text)
                )

        if not group_dict[None].ingredients:
            del group_dict[None]

        return list(group_dict.values())
