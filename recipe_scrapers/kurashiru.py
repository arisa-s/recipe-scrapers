import re
from typing import List, Optional

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup
from ._utils import normalize_string


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
        group_dict = {}  # Dictionary to hold groups by purpose

        current_purpose = None
        group_dict[None] = IngredientGroup(ingredients=[], purpose=None)

        for li in self.soup.find_all("li", class_="ingredient-list-item"):
            if "group-title" in li.get("class", []):
                purpose = normalize_string(li.get_text())
                group_dict[purpose] = IngredientGroup(ingredients=[], purpose=purpose)
                current_purpose = purpose
            elif "group-item" in li.get("class", []):
                ingredient = normalize_string(li.get_text())
                group_dict[current_purpose].ingredients.append(ingredient)
            else:
                ingredient = normalize_string(li.get_text())

                # Check for a marker like (A), (B), etc.
                marker_match = self.get_marker(ingredient)

                if marker_match:
                    purpose = marker_match
                    if purpose not in group_dict:
                        group_dict[purpose] = IngredientGroup(
                            ingredients=[], purpose=purpose
                        )
                    group_dict[purpose].ingredients.append(ingredient)
                else:
                    # If no marker, check if it starts with a non-Japanese character
                    first_char = ingredient[0]
                    if self.is_non_japanese_character(first_char):
                        purpose = first_char
                        if purpose not in group_dict:
                            group_dict[purpose] = IngredientGroup(
                                ingredients=[], purpose=purpose
                            )
                        group_dict[purpose].ingredients.append(ingredient)
                    else:
                        group_dict[None].ingredients.append(ingredient)

        if group_dict[None].ingredients.count == 0:
            del group_dict[None]
        # Convert the group_dict values to a list of IngredientGroup objects
        return list(group_dict.values())

    # Helper function to check if a string starts with a marker like (A), (B), etc.
    def get_marker(self, s):
        # This regex looks for patterns like (A), (B), (1), etc.
        match = re.match(r"^\([A-Za-z0-9]+\)", s)
        return match.group(0) if match else None

    # Helper function to check if a string starts with a non-Japanese special character
    def is_non_japanese_character(self, s):
        # This regex checks if the first character is not Kanji, Hiragana, or Katakana
        return bool(
            re.search(r"^[^\u4E00-\u9FAF\u3040-\u309F\u30A0-\u30FF\uFF66-\uFF9F]", s)
        )
