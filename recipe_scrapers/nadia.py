import re

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup
from ._utils import normalize_string
from ._utils_jp import get_minutes_jp


class Nadia(AbstractScraper):
    @classmethod
    def host(cls):
        return "oceans-nadia.com"

    def site_name(self):
        return "Nadia"

    def author(self):
        return normalize_string(
            self.soup.find("p", class_=re.compile(r"^ArtistProf_userName")).text
        )

    def title(self):
        return normalize_string(self.soup.find("h1").text)

    def category(self):
        el = self.soup.find("div", class_=re.compile(r"^pc_category"))
        return normalize_string(el.text) if el else None

    def total_time(self):
        el = self.soup.find(class_=re.compile(r"RecipeInfo_cookTimeMain"))
        return get_minutes_jp(el)

    def yields(self):
        el = self.soup.find(class_=re.compile(r"RecipeHeading_bunryoYield"))
        if el:
            match = re.search(r"(\d+)人分", el.text)
            if match:
                return f"{match.group(1)} servings"
        return None

    def image(self):
        img_container = self.soup.find("div", class_=re.compile(r"^RecipeMainImage"))
        if img_container:
            return img_container.find("img").get("src")
        video_container = self.soup.find("div", class_=re.compile(r"^RecipeNadiaVideo"))
        if video_container:
            return video_container.find("video").get("poster")

    def _ingredient_list_items(self):
        ul = self.soup.find("ul", class_=re.compile(r"^IngredientsList"))
        return ul.find_all("li") if ul else []

    def ingredients(self):
        result = []
        for li in self._ingredient_list_items():
            group_div = li.find("div", class_=re.compile(r"IngredientsList_group"))
            ing_div = li.find("div", class_=re.compile(r"IngredientsList_ingredient"))
            amt_div = li.find("div", class_=re.compile(r"IngredientsList_amount"))

            group_span = group_div.find("span") if group_div else None
            group_text = normalize_string(group_span.text) if (group_span and group_span.text.strip()) else ""
            ing_name = normalize_string(ing_div.text) if ing_div else ""
            ing_amount = normalize_string(amt_div.text) if amt_div else ""

            parts = [p for p in [group_text, ing_name, ing_amount] if p]
            result.append(" ".join(parts))
        return result

    def ingredient_groups(self):
        lis = self._ingredient_list_items()
        all_ingredients = self.ingredients()

        group_order = []
        group_dict = {}

        for idx, li in enumerate(lis):
            group_div = li.find("div", class_=re.compile(r"IngredientsList_group"))
            group_span = group_div.find("span") if group_div else None
            purpose = normalize_string(group_span.text) if (group_span and group_span.text.strip()) else None

            if purpose not in group_dict:
                group_dict[purpose] = []
                group_order.append(purpose)
            group_dict[purpose].append(all_ingredients[idx])

        return [IngredientGroup(ingredients=group_dict[p], purpose=p) for p in group_order]

    def instructions(self) -> str:
        return "\n".join(self.instructions_list())

    def instructions_list(self):
        container = self.soup.find("ul", class_=re.compile(r"^CookingProcess_list"))
        res = []
        for li in container.find_all("li"):
            p_el = li.find("p")
            if p_el:
                res.append(normalize_string(p_el.text))
        return res

    def description(self):
        el = self.soup.find("meta", attrs={"name": "description"})
        return el["content"] if el else None

    def keywords(self):
        container = self.soup.find("ul", class_=re.compile(r"^RelatedKeyWord_list"))
        if not container:
            return []
        return [normalize_string(li.text) for li in container.find_all("li")]
