"""
app.py
------
Flask entry point for CookWithMe.

Responsibilities of this file only:
  - Define HTTP routes
  - Validate input
  - Call into services/* for the real logic
  - Return clean JSON responses (or render the chat page)

All AI logic lives in services/chatbot.py, all persistence in
services/database.py, and recipe-scaling helpers in services/recipes.py.
"""

import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

from services import database
from services.chatbot import get_ai_response, ChatbotError
from services.recipes import (
    detect_dietary_preference,
    detect_cuisine_preference,
    detect_spice_level,
    detect_allergy,
    scale_recipe_ingredients,
)

# Load environment variables from .env before anything else
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")
CORS(app)

# Create the database tables (if they don't exist yet) on startup
database.init_db()


# ---------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------

@app.route("/")
def index():
    """Serve the single-page chat interface."""
    return render_template("index.html")


# ---------------------------------------------------------------------
# Chat session routes
# ---------------------------------------------------------------------

@app.route("/api/sessions", methods=["GET"])
def api_list_sessions():
    """Return all chat sessions for the sidebar, most recent first."""
    try:
        sessions = database.list_sessions()
        return jsonify({"success": True, "sessions": sessions})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sessions", methods=["POST"])
def api_create_session():
    """Start a brand new chat (used by the 'New Chat' button)."""
    try:
        session_id = database.create_session()
        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sessions/<session_id>", methods=["GET"])
def api_get_session_messages(session_id):
    """Return the full message history for a given session."""
    try:
        messages = database.get_messages(session_id)
        return jsonify({"success": True, "messages": messages})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    """Delete a chat session and its messages (used by 'Clear chat')."""
    try:
        database.delete_session(session_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sessions/<session_id>/rename", methods=["PUT"])
def api_rename_session(session_id):
    """Rename a session, e.g. auto-title it from the first message."""
    try:
        data = request.get_json(force=True)
        new_title = (data or {}).get("title", "").strip()
        if not new_title:
            return jsonify({"success": False, "error": "Title cannot be empty."}), 400
        database.rename_session(session_id, new_title[:60])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------
# Core chat route
# ---------------------------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Main chat endpoint.
    Expects JSON: { "session_id": "...", "message": "..." }
    Returns JSON: { "success": true, "reply": "...", "session_id": "..." }
    """
    try:
        data = request.get_json(force=True)
        user_message = (data or {}).get("message", "").strip()
        session_id = (data or {}).get("session_id")

        if not user_message:
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        # Create a session automatically if the client didn't have one yet
        if not session_id:
            session_id = database.create_session()

        # --- Passively learn long-term preferences from this message ---
        dietary = detect_dietary_preference(user_message)
        if dietary:
            database.set_preference("dietary_preference", dietary)

        cuisine = detect_cuisine_preference(user_message)
        if cuisine:
            database.set_preference("favorite_cuisine", cuisine)

        spice = detect_spice_level(user_message)
        if spice:
            database.set_preference("spice_level", spice)

        allergy = detect_allergy(user_message)
        if allergy:
            database.set_preference("allergies", allergy)

        # --- Save the user's message ---
        database.add_message(session_id, "user", user_message)

        # --- Build conversation history for context-aware replies ---
        history = database.get_messages(session_id)
        conversation_history = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]

        # --- Ask the AI for a reply ---
        try:
            reply = get_ai_response(conversation_history)
        except ChatbotError as e:
            return jsonify({"success": False, "error": str(e)}), 502

        # --- Save the assistant's reply ---
        database.add_message(session_id, "assistant", reply)

        # --- Auto-title new/untitled sessions from the first message ---
        sessions = {s["id"]: s for s in database.list_sessions()}
        current = sessions.get(session_id)
        if current and current["title"] == "New Chat":
            auto_title = user_message[:40] + ("..." if len(user_message) > 40 else "")
            database.rename_session(session_id, auto_title)

        return jsonify({"success": True, "reply": reply, "session_id": session_id})

    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


# ---------------------------------------------------------------------
# Preferences routes
# ---------------------------------------------------------------------

@app.route("/api/preferences", methods=["GET"])
def api_get_preferences():
    try:
        prefs = database.get_all_preferences()
        return jsonify({"success": True, "preferences": prefs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/preferences", methods=["POST"])
def api_set_preference():
    """Manually set a preference, e.g. from a settings panel."""
    try:
        data = request.get_json(force=True)
        key = (data or {}).get("key", "").strip()
        value = (data or {}).get("value", "").strip()
        if not key or not value:
            return jsonify({"success": False, "error": "Both 'key' and 'value' are required."}), 400
        database.set_preference(key, value)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------
# Recipe scaling route (deterministic helper, complements AI scaling)
# ---------------------------------------------------------------------

@app.route("/api/scale-recipe", methods=["POST"])
def api_scale_recipe():
    """
    Expects JSON:
      {
        "ingredients": ["2 cups rice", "1 onion", ...],
        "original_servings": 2,
        "new_servings": 6
      }
    """
    try:
        data = request.get_json(force=True)
        ingredients = (data or {}).get("ingredients", [])
        original_servings = float((data or {}).get("original_servings", 0))
        new_servings = float((data or {}).get("new_servings", 0))

        if not ingredients or original_servings <= 0 or new_servings <= 0:
            return jsonify({
                "success": False,
                "error": "Provide 'ingredients', a positive 'original_servings', and 'new_servings'."
            }), 400

        scaled = scale_recipe_ingredients(ingredients, original_servings, new_servings)
        return jsonify({"success": True, "scaled_ingredients": scaled})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Not found."}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error."}), 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
