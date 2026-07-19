# 🍳 CookWithMe

An AI-powered cooking assistant web app. Chat with **Chef Auto** for recipes,
ingredient-based suggestions, cooking Q&A, substitutions, recipe scaling,
dietary-preference-aware recommendations, and more.

---

## Features

- Recipe generator (ingredients, prep/cook time, difficulty, servings, steps, tips, sides)
- Ingredient-based recipe suggestions
- Cooking Q&A (technique explanations, troubleshooting)
- Ingredient substitutions
- Recipe scaling (servings up/down)
- Dietary preference support (Vegetarian, Vegan, High Protein, Keto, Gluten Free, Low Carb, Diabetic Friendly)
- Cuisine suggestions (Indian, Kerala, Chinese, Italian, Mexican, Thai, Continental)
- Meal suggestions (Breakfast, Lunch, Dinner, Snacks, Desserts, Drinks)
- Context-aware conversation with long-term memory of preferences (SQLite)
- Voice input (browser Speech Recognition, where supported)
- Copy / Print / Download-as-PDF / Share recipe buttons
- Sidebar with previous chats, new chat, clear chat
- Dark mode toggle
- Fully responsive (desktop + mobile)

---

## Tech Stack

| Layer     | Technology                          |
|-----------|--------------------------------------|
| Frontend  | HTML5, CSS3, Vanilla JavaScript      |
| Backend   | Python, Flask                        |
| AI        | OpenAI API (modular — swappable)     |
| Database  | SQLite                               |

---

## Project Structure

```
CookWithMe/
│
├── app.py                  # Flask routes
├── requirements.txt        # Python dependencies
├── .env.example             # Environment variable template
├── README.md
│
├── static/
│   ├── style.css           # Design system (theme, dark mode, responsive)
│   ├── script.js           # Chat logic, voice input, exports
│   └── images/
│
├── templates/
│   └── index.html          # Chat UI
│
├── services/
│   ├── chatbot.py          # AI integration (modular provider layer)
│   ├── recipes.py          # Recipe scaling / preference-detection helpers
│   └── database.py         # SQLite persistence
│
└── data/                   # SQLite database file lives here (auto-created)
```

---

## Setup & Installation

### 1. Clone / unzip the project
```bash
cd CookWithMe
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate it:
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Then open `.env` and set your real `OPENAI_API_KEY`:
```
OPENAI_API_KEY=sk-...your-real-key...
```

> The AI integration is modular (see `services/chatbot.py`). To use a
> different provider later, add a new `_call_<provider>()` function there
> and switch `AI_PROVIDER` in `.env`.

### 5. Run the app
```bash
python app.py
```

The app will start at **http://localhost:5000**

---

## Environment Variables Reference

| Variable            | Description                                   | Default              |
|----------------------|------------------------------------------------|-----------------------|
| `AI_PROVIDER`        | Which AI backend to use                        | `openai`             |
| `OPENAI_API_KEY`     | Your OpenAI API key                             | *(required)*          |
| `OPENAI_MODEL`       | Model name                                      | `gpt-4o-mini`         |
| `FLASK_SECRET_KEY`   | Flask session secret                            | *(change in prod)*    |
| `FLASK_ENV`          | `development` or `production`                   | `development`         |
| `FLASK_DEBUG`        | Enable Flask debug mode                         | `True`                |
| `FLASK_PORT`         | Port to run the server on                       | `5000`                |
| `DATABASE_PATH`      | Path to the SQLite database file                | `data/cookwithme.db`  |

---

## API Endpoints

| Method | Endpoint                        | Description                          |
|--------|----------------------------------|---------------------------------------|
| GET    | `/`                              | Chat interface                        |
| GET    | `/api/sessions`                  | List all chat sessions                |
| POST   | `/api/sessions`                  | Create a new chat session             |
| GET    | `/api/sessions/<id>`             | Get messages for a session            |
| DELETE | `/api/sessions/<id>`             | Delete a session                      |
| PUT    | `/api/sessions/<id>/rename`      | Rename a session                      |
| POST   | `/api/chat`                      | Send a message, get an AI reply       |
| GET    | `/api/preferences`               | Get stored user preferences           |
| POST   | `/api/preferences`               | Manually set a preference             |
| POST   | `/api/scale-recipe`              | Deterministically scale ingredients   |

---

## Notes on Safety

Chef Auto is instructed to never invent unsafe cooking advice (unsafe
temperatures, canning/fermentation shortcuts, etc.) and to say plainly when
it's uncertain about a safety-relevant detail. Always double-check
food-safety-critical information against a trusted source.

---

## License

This project is provided as-is for educational and personal use.
