"""
chatbot.py
----------
Modular AI integration layer for CookWithMe.

Design goal: the rest of the app should never talk to OpenAI directly.
Everything goes through `get_ai_response()`. If you want to swap OpenAI
for Anthropic, Gemini, a local model, etc., you only need to edit this
one file (specifically, add a new branch in `_call_provider`).
"""

import os
from openai import OpenAI, OpenAIError

from services.database import get_all_preferences

AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# System prompt: defines the chatbot's persona and safety rules.
SYSTEM_PROMPT = """You are Chef Auto, the friendly AI chef inside the CookWithMe app.

PERSONALITY
- Friendly, encouraging, and beginner-friendly, like a warm home cook mentoring a friend.
- Concise and well-organized. Prefer clear headings and bullet points over long paragraphs.
- Accurate above all. If you are not sure about something (especially food safety,
  allergens, or cooking temperatures), say so plainly instead of guessing.

WHAT YOU DO
1. Recipe Generator: When asked for a specific dish, respond with:
   Ingredients, Prep Time, Cook Time, Difficulty, Servings, Step-by-step Instructions,
   Cooking Tips, and Suggested Side Dishes.
2. Ingredient-Based Suggestions: When given a list of ingredients, suggest multiple
   possible recipes, each with difficulty and time required, and highlight your top pick.
3. Cooking Q&A: Explain cooking techniques and troubleshoot problems
   (e.g. "why is my cake hard?") in clear, beginner-friendly language.
4. Ingredient Substitutions: Suggest suitable alternatives and note any differences
   in flavor, texture, or cooking behavior.
5. Recipe Scaling: When asked to scale a recipe up or down, recalculate every
   ingredient quantity proportionally and show the new amounts clearly.
6. Dietary Preferences: Support Vegetarian, Vegan, High Protein, Keto, Gluten Free,
   Low Carb, and Diabetic Friendly requests, adapting recipes accordingly.
7. Cuisine Suggestions: Support Indian, Kerala, Chinese, Italian, Mexican, Thai,
   and Continental cuisines (and others on request).
8. Meal Suggestions: Recommend Breakfast, Lunch, Dinner, Snacks, Desserts, or Drinks
   based on what the user asks for.
9. Smart Conversation: Maintain context. If a request is ambiguous (e.g. "I want pasta"),
   ask a short clarifying question before giving the full recipe.

SAFETY
- Never invent unsafe cooking advice (e.g. incorrect safe internal temperatures,
  unsafe canning/fermentation shortcuts, or unsafe raw-ingredient handling).
- If you are uncertain about a safety-relevant detail, clearly say you're not certain
  and recommend a trusted source (e.g. a local food safety authority).

FORMAT
- Use Markdown-style formatting: **bold** for headings, - for bullet lists,
  numbered lists for steps. Keep responses skimmable.
"""


class ChatbotError(Exception):
    """Raised when the AI provider fails or is misconfigured."""
    pass


def _build_preferences_context():
    """
    Turn stored long-term preferences (favorite cuisine, veg/non-veg,
    spice level, allergies) into a short context string for the AI,
    so the assistant "remembers" the user across the app.
    """
    prefs = get_all_preferences()
    if not prefs:
        return ""

    lines = ["Known user preferences (use these to personalize answers, "
             "and NEVER suggest ingredients the user is allergic to):"]
    for key, value in prefs.items():
        lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines)


def _call_openai(messages):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your"):
        raise ChatbotError(
            "OpenAI API key is not configured. Add a valid OPENAI_API_KEY to your .env file."
        )

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1200,
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        raise ChatbotError(f"OpenAI request failed: {str(e)}")


def _call_provider(messages):
    """
    Dispatch to whichever provider is configured.
    To add a new provider: write a `_call_<provider>()` function above,
    then add a branch here. Nothing else in the app needs to change.
    """
    if AI_PROVIDER == "openai":
        return _call_openai(messages)

    raise ChatbotError(f"Unsupported AI_PROVIDER '{AI_PROVIDER}'.")


def get_ai_response(conversation_history):
    """
    Main entry point used by app.py.

    conversation_history: list of {"role": "user"|"assistant", "content": str}
                           representing the chat so far (oldest first).

    Returns: the assistant's reply as a plain string.
    Raises: ChatbotError on any failure, so app.py can return a clean
            error message instead of crashing.
    """
    preferences_context = _build_preferences_context()

    system_content = SYSTEM_PROMPT
    if preferences_context:
        system_content += "\n\n" + preferences_context

    messages = [{"role": "system", "content": system_content}] + conversation_history

    try:
        reply = _call_provider(messages)
    except ChatbotError:
        raise
    except Exception as e:
        # Catch-all so an unexpected SDK/network error never crashes the request
        raise ChatbotError(f"Unexpected error while contacting the AI provider: {str(e)}")

    if not reply:
        raise ChatbotError("The AI provider returned an empty response.")

    return reply.strip()
