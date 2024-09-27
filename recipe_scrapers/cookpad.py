import re
from typing import List

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup


class CookPad(AbstractScraper):
    @classmethod
    def host(cls):
        return "cookpad.com"

    def site_name(self):
        return "Cookpad"

    def ingredient_groups(self) -> List[IngredientGroup]:
        group_dict = {}  # Dictionary to hold groups by purpose

        for li in self.soup.find_all("li", class_="justified-quantity-and-name"):
            span_text = li.find("span").get_text(strip=True)
            bdi_text = li.find("bdi").get_text(strip=True)

            # Combine the ingredient name with the quantity if available
            ingredient = f"{span_text} {bdi_text}".strip()

            # Get the first character of the span text
            first_char = span_text[0]

            # If it's a headline (grouping category)
            if "headline" in li.get("class", []):
                purpose = span_text
                if purpose not in group_dict:
                    group_dict[purpose] = IngredientGroup(
                        ingredients=[], purpose=purpose
                    )
                group_dict[purpose].ingredients.append(ingredient)

            # Check if the ingredient starts with a non-Japanese special character
            elif self.is_non_japanese_character(first_char):
                purpose = first_char
                if purpose not in group_dict:
                    group_dict[purpose] = IngredientGroup(
                        ingredients=[], purpose=purpose
                    )
                group_dict[purpose].ingredients.append(ingredient)

            else:
                # For ingredients without a special character or headline, assume no specific purpose
                purpose = None
                if purpose not in group_dict:
                    group_dict[purpose] = IngredientGroup(
                        ingredients=[], purpose=purpose
                    )
                group_dict[purpose].ingredients.append(ingredient)

        # Convert the group_dict values to a list of IngredientGroup objects
        return list(group_dict.values())

    # Helper function to check if a string starts with a non-Japanese special character
    def is_non_japanese_character(self, s):
        # This regex checks if the first character is not Kanji, Hiragana, or Katakana
        return bool(
            re.search(r"^[^\u4E00-\u9FAF\u3040-\u309F\u30A0-\u30FF\uFF66-\uFF9F]", s)
        )
