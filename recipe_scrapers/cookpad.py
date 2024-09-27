from ._abstract import AbstractScraper
from ._grouping_utils import group_ingredients


class CookPad(AbstractScraper):
    @classmethod
    def host(cls):
        return "cookpad.com"

    def site_name(self):
        return "Cookpad"

    def ingredient_groups(self):
        res = group_ingredients(
            self.ingredients(),
            self.soup,
            ".headline li",
            ".not-headline li",
        )
        print(res)
        return res
