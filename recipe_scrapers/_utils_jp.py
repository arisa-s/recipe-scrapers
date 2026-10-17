import html
import inspect
import math
import re

import isodate

from ._exceptions import ElementNotFoundInHtml

FRACTIONS = {
    "½": 0.5,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "¼": 0.25,
    "¾": 0.75,
    "⅕": 0.2,
    "⅖": 0.4,
    "⅗": 0.6,
    "⅘": 0.8,
    "⅙": 1 / 6,
    "⅚": 5 / 6,
    "⅛": 0.125,
    "⅜": 0.375,
    "⅝": 0.625,
    "⅞": 0.875,
}

TIME_REGEX = re.compile(
    r"(?:\D*(?P<days>\d+)\s*(?:days|D))?"
    r"(?:\D*(?P<hours>[\d.\s/?¼½¾⅓⅔⅕⅖⅗]+)\s*(?:hours|hrs|hr|h|óra|:))?"
    r"(?:\D*(?P<minutes>\d+)\s*(?:minutes|mins|min|m|perc|$))?"
    r"(?:\D*(?P<seconds>\d+)\s*(?:seconds|secs|sec|s))?",
    re.IGNORECASE,
)
SERVE_REGEX_NUMBER = re.compile(r"(\D*(?P<items>\d+)?\D*)")

SERVE_REGEX_ITEMS = re.compile(
    r"\bsandwiches\b |\btacquitos\b | \bmakes\b | \bcups\b | \bappetizer\b | \bporzioni\b | \bcookies\b | \b(large |small )?buns\b",
    flags=re.I | re.X,
)

SERVE_REGEX_TO = re.compile(r"\d+(\s+to\s+|-)\d+", flags=re.I | re.X)

RECIPE_YIELD_TYPES = (
    ("dozen", "dozen"),
    ("batch", "batches"),
    ("cake", "cakes"),
    ("sandwich", "sandwiches"),
    ("bun", "buns"),
    ("cookie", "cookies"),
    ("muffin", "muffins"),
    ("cupcake", "cupcakes"),
    ("loaf", "loaves"),
    ("pie", "pies"),
    ("cup", "cups"),
    ("pint", "pints"),
    ("gallon", "gallons"),
    ("ounce", "ounces"),
    ("pound", "pounds"),
    ("gram", "grams"),
    ("liter", "liters"),
    ("piece", "pieces"),
    ("layer", "layers"),
    ("scoop", "scoops"),
    ("bar", "bars"),
    ("patty", "patties"),
    ("hamburger bun", "hamburger buns"),
    ("pancake", "pancakes"),
    ("item", "items"),
    # ... add more types as needed, in (singular, plural) format ...
)


def format_diet_name(diet_input):
    replacements = {
        # https://schema.org/RestrictedDiet
        "DiabeticDiet": "Diabetic Diet",
        "GlutenFreeDiet": "Gluten Free Diet",
        "HalalDiet": "Halal Diet",
        "HinduDiet": "Hindu Diet",
        "KosherDiet": "Kosher Diet",
        "LowCalorieDiet": "Low Calorie Diet",
        "LowFatDiet": "Low Fat Diet",
        "LowLactoseDiet": "Low Lactose Diet",
        "LowSaltDiet": "Low Salt Diet",
        "VeganDiet": "Vegan Diet",
        "VegetarianDiet": "Vegetarian Diet",
    }
    if "https://schema.org/" in diet_input:
        diet_input = diet_input.replace("https://schema.org/", "")

    for key, value in replacements.items():
        if key in diet_input:
            return value

    return diet_input


def _extract_fractional(input_string: str) -> float:
    input_string = input_string.strip()

    # Handling mixed numbers with unicode fractions e.g., '1⅔'
    for unicode_fraction, fraction_part in FRACTIONS.items():
        if unicode_fraction in input_string:
            whole_number_part, _, _ = input_string.partition(unicode_fraction)

            whole_number = float(whole_number_part or 0)
            return whole_number + fraction_part

    if input_string in FRACTIONS:
        return FRACTIONS[input_string]

    try:
        return float(input_string)
    except ValueError:
        pass

    if " " in input_string and "/" in input_string:
        whole_part, fractional_part = input_string.split(" ", 1)
        numerator, denominator = fractional_part.split("/")
        return float(whole_part) + float(numerator) / float(denominator)

    elif "/" in input_string:
        numerator, denominator = input_string.split("/")
        return float(numerator) / float(denominator)

    raise ValueError(f"Unrecognized fraction format: '{input_string}'")


def get_minutes_jp(element):
    if element is None:
        raise ElementNotFoundInHtml(element)

    # If element is a BeautifulSoup Tag, extract its text content
    if hasattr(element, "text"):
        element = element.text

    try:
        return int(element)
    except ValueError:
        pass

    if not isinstance(element, str):
        raise ValueError("Unexpected format for time element")

    time_text = element.strip()

    # Handle Japanese time units and ranges (e.g., '12〜15分' or '12分〜15分')
    time_text = re.sub(r"〜", " to ", time_text)  # Normalize Japanese '〜' to 'to'

    # Handle cases like '12-15 分'
    if "-" in time_text:
        _min, _, time_text = time_text.partition("-")
    if " to " in time_text:
        _min, _to, time_text = time_text.partition(" to ")

    if time_text is None:
        return None

    # Handle ISO8601 format if encountered (less likely for Japanese recipes)
    if time_text.startswith("P") and "T" in time_text:
        try:
            duration = isodate.parse_duration(time_text)
            total_minutes = math.ceil(duration.total_seconds() / 60)
            return None if total_minutes == 0 else total_minutes
        except Exception:
            pass

    # Define regex for Japanese time units
    TIME_REGEX_JP = re.compile(
        r"(?:\D*(?P<days>\d+)\s*(?:日))?"
        r"(?:\D*(?P<hours>[\d.\s/?¼½¾⅓⅔⅕⅖⅗]+)\s*(?:時間))?"
        r"(?:\D*(?P<minutes>\d+)\s*(?:分))?"
        r"(?:\D*(?P<seconds>\d+)\s*(?:秒))?",
        re.IGNORECASE,
    )

    time_units = TIME_REGEX_JP.search(time_text).groupdict()
    if not any(time_units.values()):
        return None

    minutes_matched = time_units.get("minutes")
    hours_matched = time_units.get("hours")
    days_matched = time_units.get("days")
    seconds_matched = time_units.get("seconds")

    # Convert matched time units to total minutes
    days = float(days_matched) if days_matched else 0
    hours = _extract_fractional(hours_matched) if hours_matched else 0
    minutes = float(minutes_matched) if minutes_matched else 0
    seconds = float(seconds_matched) if seconds_matched else 0

    total_minutes = minutes + (hours * 60) + (days * 24 * 60) + (seconds / 60)

    # Round to nearest whole number
    return round(total_minutes)
