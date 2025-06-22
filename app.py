from flask import Flask, render_template, request, jsonify
import json
from fuzzywuzzy import fuzz
from openai import OpenAI
import os

app = Flask(__name__)

with open("final_cleaned_data.json", encoding="utf-8") as f:
    courses = json.load(f)
with open("category_area_map.json", encoding="utf-8") as f:
    category_area_map = json.load(f)

api_key = os.getenv("OPENAI_API_KEY")  # נשלף מהסביבה
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
    stage = user_state["stage"]

    if stage not in ["subcategory", "area"]:
        if not all('\u0590' <= char <= '\u05EA' or not char.isalpha() for char in msg):
            return jsonify({"response": "Sorry, I only support communication in Hebrew 🇮🇱", "options": []})

    if stage == "welcome":
        user_state["stage"] = "intro_wait"
        return jsonify({
            "response": "היי! אני צ'אטבוט שמומחה בעזרה לחיילים משוחררים 🎓<br>אני כאן כדי לעזור לך למצוא קורסים שמתאימים בדיוק לך – לפי תחום, אזור ומידע נוסף.<br><br>האם תרצה לנסות? ✨",
            "options": []
        })

    if msg.lower() in ["כן", "יאללה", "בוא נתחיל", "קדימה", "אפשר להתחיל"] and stage == "intro_wait":
        user_state["stage"] = "category"
        options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
        return jsonify({
            "response": "מעולה! לפניך מספר שאלות שיעזרו לי למצוא את הקורס המתאים ביותר עבורך ✨<br><br>איזה תחום מעניין אותך?",
            "options": options
        })

    if any(word in msg.lower() for word in ["מרוויח", "שכר", "משכורת", "הכנסה", "כמה מקבלים", "כמה משתכרים", "כמה השכר", "השכר הממוצע"]):
        gpt_reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "ענה בעברית בלבד בקצרה"},
                {"role": "user", "content": msg}
            ]
        )
        return jsonify({"response": gpt_reply.choices[0].message.content, "options": []})

    if msg.lower() in ["לא אהבתי", "אפשר משהו אחר", "תן משהו אחר"]:
        user_state.update({"stage": "category", "category": None, "subcategories": [], "area": None})
        options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
        return jsonify({
            "response": "אין בעיה! בוא ננסה שוב למצוא משהו חדש שתאהב 💡<br>מה התחום שמעניין אותך?",
            "options": options
        })

    if stage == "category":
        user_state["category"] = msg
        user_state["stage"] = "subcategory"
        subcategories = sorted(set(c.get("תת קטגוריה") for c in courses if c["קטגוריה"] == msg and c.get("תת קטגוריה")))
        if subcategories:
            return jsonify({
                "response": "מעולה! באיזה תתי נושאים אתה מעוניין? אפשר לבחור יותר מאחד.",
                "options": subcategories
            })
        else:
            user_state["stage"] = "area"
            areas = category_area_map.get(msg, [])
            return jsonify({
                "response": "מצוין! באיזה אזור בארץ אתה מעוניין ללמוד?",
                "options": areas
            })

    if stage == "subcategory":
        selected = [s.strip() for s in msg.split(",") if s.strip()]
        all_valid = set(c.get("תת קטגוריה") for c in courses if c["קטגוריה"] == user_state["category"] and c.get("תת קטגוריה"))
        matches = [s for s in selected if s in all_valid]
        if not matches:
            return jsonify({
                "response": "מצטער, לא זיהיתי את תתי הנושאים שבחרת. נסה שוב מתוך האפשרויות שהצגתי 😊",
                "options": sorted(all_valid)
            })
        user_state["subcategories"] = matches
        user_state["stage"] = "area"
        areas = category_area_map.get(user_state["category"], [])
        return jsonify({
            "response": "יופי! באיזה אזור בארץ אתה מעוניין ללמוד?",
            "options": areas
        })

    if stage == "area":
        user_state["area"] = msg
        user_state["stage"] = "done"
        matches = []
        for c in courses:
            if c["קטגוריה"] != user_state["category"]:
                continue
            if user_state["subcategories"] and c.get("תת קטגוריה") not in user_state["subcategories"]:
                continue
            if fuzz.partial_ratio(c.get("אזור", ""), msg) > 80:
                matches.append(c)

        if matches:
            previews = []
            details = {}
            for idx, c in enumerate(matches):
                cid = f"course_{idx}"
                previews.append(
                    f"<div class='course-preview' onclick=\"fetchCourseDetails('{cid}')\">"
                    f"📚 {c['שם הקורס']}<br>"
                    f"🏙 עיר: {c.get('עיר', 'לא צוינה')}<br>"
                    f"💰 עלות: {c.get('עלות', 'לא צוינה')}<br>"
                    f"🕒 משך קורס: {c.get('משך קורס', 'לא ידוע')}<br>"
                    f"📍 כתובת: {c.get('כתובת', 'לא זמינה')}</div>"
                )
                email = c.get("מייל", "")
                email_link = (
                    f"<a href='mailto:{email}?subject=התעניינות בקורס לחיילים משוחררים"
                    f"&body=שלום, אני מתעניין בקורס. אשמח לפרטים נוספים. תודה!' target='_blank'>{email or 'לא זמין'}</a>"
                )
                details[cid] = f"📞 איש קשר: {c.get('מספר פלאפון', 'לא ידוע')}<br>📧 מייל: {email_link}"
            return jsonify({
                "response": "נמצאו קורסים מתאימים!<br><br>" + "<br><br>".join(previews) + "<br><br>🔍 לחץ על קורס כדי לראות את פרטי הקשר",
                "options": [],
                "details": details
            })
        else:
            user_state["stage"] = "category"
            options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
            return jsonify({
                "response": "לא נמצאו קורסים. רוצה שננסה שוב עם תחום אחר?",
                "options": options
            })

    return jsonify({"response": "שאלה כללית? אני מתמחה בעזרה עם קורסים בלבד 🙂", "options": []})

if __name__ == "__main__":
    app.run(debug=True)
