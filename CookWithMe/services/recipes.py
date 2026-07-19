"""
recipes.py
----------
Lightweight helper utilities that support the chatbot around recipe-related
logic that doesn't need a full AI round-trip:
  - Detecting dietary preference / allergy / spice-level statements so they
    can be saved to long-term memory automatically.
  - A basic ingredient-quantity scaler, used as a local fallback/helper
    (the AI also does this conversationally, but this gives the app a
    deterministic option for simple "servings x2" style requests).

Keeping this logic separate from chatbot.py keeps the AI-integration file
focused purely on talking to the LLM, per the "separate frontend, backend,
AI, and database logic" requirement.
"""

import re

DIETARY_KEYWORDS = [
    "vegetarian", "vegan", "high protein", "keto", "gluten free",
    "low carb", "diabetic friendly", "non-vegetarian", "non vegetarian",
]

CUISINE_KEYWORDS = [
    "indian", "kerala", "chinese", "italian", "mexican", "thai", "continental",
]

SPICE_LEVELS = ["mild", "medium", "spicy", "very spicy", "no spice"]


def detect_dietary_preference(text):
    """Return the first dietary keyword found in free text, or None."""
    lowered = text.lower()
    for keyword in DIETARY_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def detect_cuisine_preference(text):
    lowered = text.lower()
    for keyword in CUISINE_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def detect_spice_level(text):
    lowered = text.lower()
    for level in SPICE_LEVELS:
        if level in lowered:
            return level
    return None


def detect_allergy(text):
    """
    Very small heuristic parser: looks for phrases like
    "I'm allergic to peanuts" or "allergic to shellfish".
    Returns the allergen string, or None.
    """
    match = re.search(r"allergic to ([a-zA-Z ,]+)", text.lower())
    if match:
        return match.group(1).strip().rstrip(".")
    return None


def scale_ingredient_line(line, factor):
    """
    Scale the leading numeric quantity in a single ingredient line by `factor`.
    Example: scale_ingredient_line("2 cups rice", 3) -> "6 cups rice"

    Only handles simple leading numbers/fractions - the AI handles more
    complex scaling conversationally. This is a deterministic helper for
    simple, predictable cases (e.g. a "Scale Recipe" UI control).
    """
    match = re.match(r"^\s*(\d+(\.\d+)?|\d+/\d+)\s*(.*)", line)
    if not match:
        return line  # no leading quantity found, return unchanged

    quantity_str, _, rest = match.groups()

    if "/" in quantity_str:
        numerator, denominator = quantity_str.split("/")
        quantity = float(numerator) / float(denominator)
    else:
        quantity = float(quantity_str)

    scaled = quantity * factor
    # Format nicely: drop trailing .0, keep up to 2 decimal places otherwise
    if scaled == int(scaled):
        scaled_str = str(int(scaled))
    else:
        scaled_str = f"{scaled:.2f}".rstrip("0").rstrip(".")

    return f"{scaled_str} {rest}".strip()


def scale_recipe_ingredients(ingredient_lines, original_servings, new_servings):
    """
    Scale a full list of ingredient lines from original_servings to new_servings.
    Returns a new list of scaled ingredient strings.
    """
    if original_servings <= 0:
        raise ValueError("original_servings must be greater than 0")

    factor = new_servings / original_servings
    return [scale_ingredient_line(line, factor) for line in ingredient_lines]
