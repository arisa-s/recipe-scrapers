import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from ._utils import normalize_string


@dataclass
class IngredientGroup:
    ingredients: List[str]
    purpose: Optional[str] = (
        None  # this group of ingredients is {purpose} (e.g. "For the dressing")
    )


def score_sentence_similarity(first: str, second: str) -> float:
    """Calculate Dice coefficient for two strings.

    The dice coefficient is a measure of similarity that accounts for
    the length of the strings, determined by the proportion of shared bigrams. This normalization
    ensures the score is less biased towards shorter strings.

    Parameters
    ----------
    first : str
        The first input string.
    second : str
        The second input string.

    Returns
    -------
    float
        The similarity score between 0 and 1, where 0 indicates no shared bigrams and
        1 indicates identical strings.
    """

    if first == second:
        return 1

    if len(first) < 2 or len(second) < 2:
        return 0

    first_bigrams = {first[i : i + 2] for i in range(len(first) - 1)}
    second_bigrams = {second[i : i + 2] for i in range(len(second) - 1)}

    intersection = len(first_bigrams & second_bigrams)

    return 2 * intersection / (len(first_bigrams) + len(second_bigrams))


def best_match(test_string: str, target_strings: List[str]) -> str:
    """Find the best match for a given test string within a list of target strings.

    This function utilizes the score_sentence_similarity function to compare the test string
    against each target string. The target string with the highest similarity score to the
    test string is returned as the best match.

    Parameters
    ----------
    test_string : str
        The string to find the best match for.
    target_strings : List[str]
        A list of strings to compare against the test string.

    Returns
    -------
    str
        The string from target_strings that has the highest similarity score with test_string.
    """
    scores = [
        score_sentence_similarity(test_string, target) for target in target_strings
    ]
    best_match_index = max(range(len(scores)), key=scores.__getitem__)

    return target_strings[best_match_index]


def group_ingredients(
    ingredients_list: List[str],
    soup: BeautifulSoup,
    group_heading: str,
    group_element: str,
) -> List[IngredientGroup]:
    """
    Group ingredients into sublists according to the heading in the recipe.

    This method groups ingredients by extracting headings and corresponding elements
    based on provided CSS selectors. If no groupings are present, it creates a single
    group with all ingredients. It ensures ingredient groupings match those in
    the .ingredients() method of a scraper by comparing the text against the ingredients list.

    Parameters
    ----------
    ingredients_list : List[str]
        Ingredients extracted by the scraper.
    soup : BeautifulSoup
        Parsed HTML of the recipe page.
    group_heading : str
        CSS selector for ingredient group headings.
    group_element : str
        CSS selector for ingredient list items.

    Returns
    -------
    List[IngredientGroup]
        groupings of ingredients categorized by their purpose or heading.

    Raises
    -------
    ValueError
        If the number of elements selected does not match the length of ingredients_list.
    """

    found_ingredients = soup.select(group_element)
    if len(found_ingredients) != len(ingredients_list):
        raise ValueError(
            f"Found {len(found_ingredients)} grouped ingredients but was expecting to find {len(ingredients_list)}."
        )

    groupings: Dict[Optional[str], List[str]] = defaultdict(list)
    current_heading = None

    elements = soup.select(f"{group_heading}, {group_element}")
    for element in elements:
        if element in element.parent.select(group_heading):
            current_heading = normalize_string(element.text) or None
            if current_heading not in groupings:
                groupings[current_heading] = []
        else:
            ingredient_text = normalize_string(element.text)
            matched_ingredient = best_match(ingredient_text, ingredients_list)
            groupings[current_heading].append(matched_ingredient)

    return [
        IngredientGroup(purpose=heading, ingredients=items)
        for heading, items in groupings.items()
        if items != []
    ]


def get_marker(ingredient: str) -> Optional[str]:
    """Checks if the ingredient starts with a marker like (A), (B), etc."""
    match = re.match(r"^\([A-Za-z0-9]+\)", ingredient)
    return match.group(0) if match else None


def is_non_japanese_character(first_char: str) -> bool:
    """Checks if the first character is not Kanji, Hiragana, or Katakana."""
    return bool(
        re.search(
            r"^[^\u4E00-\u9FAF\u3040-\u309F\u30A0-\u30FF\uFF66-\uFF9F]", first_char
        )
    )


def group_ingredients_jp(
    soup, ingredient_selector: str, purpose_selector: str
) -> List[IngredientGroup]:
    """
    Groups ingredients based on purpose markers, non-Japanese characters, or no markers.

    :param soup: BeautifulSoup object representing the page content.
    :param ingredient_selector: CSS class or tag for selecting ingredients.
    :param purpose_selector: CSS class for selecting ingredient group purposes.
    :return: List of IngredientGroup objects.
    """
    group_dict: Dict[Optional[str], IngredientGroup] = {
        None: IngredientGroup(ingredients=[], purpose=None)
    }
    current_purpose: Optional[str] = None

    for li in soup.find_all("li", class_=ingredient_selector):
        if purpose_selector in li.get("class", []):
            purpose = normalize_string(li.get_text())
            group_dict[purpose] = IngredientGroup(ingredients=[], purpose=purpose)
            current_purpose = purpose
        else:
            ingredient = normalize_string(li.get_text())
            marker_match = get_marker(ingredient)

            if marker_match:
                purpose = marker_match
                if purpose not in group_dict:
                    group_dict[purpose] = IngredientGroup(
                        ingredients=[], purpose=purpose
                    )
                group_dict[purpose].ingredients.append(ingredient)
            else:
                first_char = ingredient[0]
                if is_non_japanese_character(first_char):
                    purpose = first_char
                    if purpose not in group_dict:
                        group_dict[purpose] = IngredientGroup(
                            ingredients=[], purpose=purpose
                        )
                    group_dict[purpose].ingredients.append(ingredient)
                else:
                    group_dict[current_purpose].ingredients.append(ingredient)

    if not group_dict[None].ingredients:
        del group_dict[None]

    return list(group_dict.values())
