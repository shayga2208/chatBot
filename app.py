from flask import Flask, render_template, request, jsonify
import json
from fuzzywuzzy import fuzz
from openai import OpenAI

app = Flask(__name__)

with open("final_cleaned_data.json", encoding="utf-8") as f:
    courses = json.load(f)
with open("category_area_map.json", encoding="utf-8") as f:
    category_area_map = json.load(f)

api_key = "YOUR_API_KEY"
client = OpenAI(api_key=api_key)


user_state = {
    "stage": "welcome",
    "category": None,
    "subcategories": [],
    "area": None
}

@app.route("/")
def index():
    user_state.update({"stage": "welcome", "category": None, "subcategories": [], "area": None})
    return render_template("index.html")

@app.route("/reset", methods=["POST"])
def reset():
    user_state.update({"stage": "welcome", "category": None, "subcategories": [], "area": None})
    return jsonify({"response": "השיחה אופסה. אפשר להתחיל מחדש 🙂", "options": []})

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()

    if not all('֐' <= char <= 'ת' or not char.isalpha() for char in msg):
        return jsonify({"response": "מצטער, אני מתמחה רק במענה בשפה העברית 🇮🇱", "options": []})

    stage = user_state["stage"]
    response = ""
    options = []

    if stage == "welcome":
        user_state["stage"] = "intro_wait"
        return jsonify({
            "response": """היי! אני צ'אטבוט שמומחה בעזרה לחיילים משוחררים 🎓
אני כאן כדי לעזור לך למצוא קורסים שמתאימים בדיוק לך – לפי תחום, אזור ומידע נוסף.

האם תרצה לנסות? ✨""",
            "options": []
        })

    if msg.lower() in ["כן", "יאללה", "בוא נתחיל", "קדימה", "אפשר להתחיל"] and stage == "intro_wait":
        user_state["stage"] = "category"
        response = "מעולה! לפניך מספר שאלות שיעזרו לי למצוא את הקורס המתאים ביותר עבורך ✨\n\nאיזה תחום מעניין אותך?"
        options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
        return jsonify({"response": response, "options": options})

    response = "שאלה כללית? אני מתמחה בעזרה עם קורסים בלבד 🙂"
    return jsonify({"response": response, "options": []})

if __name__ == "__main__":
    app.run(debug=True)
