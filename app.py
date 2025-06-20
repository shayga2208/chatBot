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
    return render_template("index.html")

@app.route("/reset", methods=["POST"])
def reset():
    user_state.update({"stage": "welcome", "category": None, "subcategories": [], "area": None})
    return jsonify({"response": "השיחה אופסה. אפשר להתחיל מחדש 🙂", "options": []})

@app.route("/chat", methods=["POST"])
def chat():
    msg = request.json.get("message", "").strip()

    if not all('\u0590' <= char <= '\u05EA' or not char.isalpha() for char in msg):
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
        response = "אין בעיה! בוא ננסה שוב למצוא משהו חדש שתאהב 💡\nמה התחום שמעניין אותך?"
        options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
        return jsonify({"response": response, "options": options})

    if stage == "category":
        user_state["category"] = msg
        user_state["stage"] = "subcategory"
        subcategories = sorted(set(c.get("תת קטגוריה") for c in courses if c["קטגוריה"] == msg and c.get("תת קטגוריה")))
        if subcategories:
            response = "מעולה! באיזה תתי נושאים אתה מעוניין? אפשר לבחור יותר מאחד."
            options = subcategories
        else:
            user_state["stage"] = "area"
            response = "מצוין! באיזה אזור בארץ אתה מעוניין ללמוד?"
        return jsonify({"response": response, "options": options})

    if stage == "subcategory":
        user_state["subcategories"] = [s.strip() for s in msg.split(",") if s.strip()]
        user_state["stage"] = "area"
        areas = category_area_map.get(user_state["category"], [])
        response = "יופי! באיזה אזור בארץ אתה מעוניין ללמוד?"
        options = areas
        return jsonify({"response": response, "options": options})

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
            preview_lines = []
            detailed_info = {}
            for idx, c in enumerate(matches):
                cid = f"course_{idx}"
                preview_lines.append(
                    f"<div class='course-preview' onclick=\"fetchCourseDetails('{cid}')\">"
                    f"📚 {c['שם הקורס']}<br>"
                    f"🏙 עיר: {c.get('עיר', 'לא צוינה')}<br>"
                    f"💰 עלות: {c.get('עלות', 'לא צוינה')}<br>"
                    f"🕒 משך קורס: {c.get('משך קורס', 'לא ידוע')}<br>"
                    f"📍 כתובת: {c.get('כתובת', 'לא זמינה')}"
                    f"</div>"
                )
                email = c.get("מייל", "")
                email_link = (
                    f"<a href='mailto:{email}?subject=התעניינות בקורס לחיילים משוחררים"
                    f"&body=שלום, הגעתי אליכם דרך הבוט של הקורסים לחיילים משוחררים ואני מתעניין בקורס. "
                    f"אשמח שתחזרו אליי עם פרטים נוספים. תודה!' target='_blank'>{email or 'לא זמין'}</a>"
                )
                detailed_info[cid] = (
                    f"📞 איש קשר: {c.get('מספר פלאפון', 'לא ידוע')}<br>"
                    f"📧 מייל: {email_link}"
                )
            response = (
                "נמצאו קורסים מתאימים!<br><br>" +
                "<br><br>".join(preview_lines) +
                "<br><br>🔍 לחץ על קורס כדי לראות את פרטי הקשר"
            )
            return jsonify({"response": response, "options": [], "details": detailed_info})
        else:
            response = "לא נמצאו קורסים. רוצה שננסה שוב עם תחום אחר?"
            user_state["stage"] = "category"
            options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
            return jsonify({"response": response, "options": options})

    response = "שאלה כללית? אני מתמחה בעזרה עם קורסים בלבד 🙂"
    return jsonify({"response": response, "options": []})

if __name__ == "__main__":
    app.run(debug=True)

