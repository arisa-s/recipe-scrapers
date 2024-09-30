import re

from ._abstract import AbstractScraper
from ._grouping_utils import IngredientGroup
from ._utils import normalize_string
from ._utils_jp import get_minutes_jp


class Nadia(AbstractScraper):
    @classmethod
    def host(self):
        return "oceans-nadia.com"

    def site_name(self):
        return "Nadia"

    def author(self):
        return normalize_string(
            self.soup.find("p", class_=re.compile(r"^ArtistProf_userName")).text
        )

    def title(self):
        return normalize_string(self.soup.find("h1").text)

    # !!
    def category(self):
        return normalize_string(
            self.soup.find("div", class_=re.compile(r"^pc_category")).text
        )

    def total_time(self):
        return get_minutes_jp(
            self.soup.find("li", class_=re.compile(r"^RecipeInfo_time"))
        )

    def yields(self):
        yield_info = self.soup.find("div", class_="CommonHeading_heading02___RmcC")
        if yield_info:
            # Find text that matches "XX人分"
            text = yield_info.text
            match = re.search(r"(\d+)人分", text)
            if match:
                return int(match.group(1))

        return None

    def image(self):
        img_container = self.soup.find("div", class_=re.compile(r"^RecipeMainImage"))
        if img_container:
            return img_container.find("img").get("src")
        video_container = self.soup.find("div", class_=re.compile(r"^RecipeNadiaVideo"))
        if video_container:
            return video_container.find("video").get("poster")

    def ingredients(self):
        ingredients = self.soup.find(
            "ul", class_=re.compile(r"^IngredientsList")
        ).find_all("li")
        return [normalize_string(ingredient.text) for ingredient in ingredients]

    def instructions(self) -> str:
        return "\n".join(self.instructions_list())

    def instructions_list(self):
        instructions_container = self.soup.find(
            "ul", class_=re.compile(r"^CookingProcess_list")
        )
        res = []
        for li in instructions_container.find_all("li"):
            instruction = normalize_string(li.find("p").text)
            res.append(instruction)
        return res

    def description(self):
        description_element = self.soup.find("meta", attrs={"name": "description"})
        return description_element["content"]

    def keywords(self):
        container = self.soup.find("ul", class_=re.compile(r"^RelatedKeyWord_list"))
        return [normalize_string(li.text) for li in container.find_all("li")]
