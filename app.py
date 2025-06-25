from flask import Flask, render_template, request, jsonify
import json
from fuzzywuzzy import fuzz
from openai import OpenAI

app = Flask(__name__)

with open("final_cleaned_data.json", encoding="utf-8") as f:
    courses = json.load(f)
with open("category_area_map.json", encoding="utf-8") as f:
    category_area_map = json.load(f)

api_key = os.getenv("OPENAI_API_KEY")  # נשלף מרנדר
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
        return jsonify({"response": "Sorry, I only respond in Hebrew 🇮🇱", "options": []})

    stage = user_state["stage"]
    response = ""
    options = []

    # --- שאלות על שכר או ביקוש ---
    salary_keywords = ["מרוויח", "שכר", "משכורת", "הכנסה", "כמה מקבלים", "כמה משתכרים", "כמה השכר", "השכר הממוצע"]
    demand_keywords = ["ביקוש", "דרישה", "נחוץ", "נדרש", "יש עבודה", "יש ביקוש", "יש צורך"]

    if any(word in msg.lower() for word in salary_keywords + demand_keywords):
        topic = None
        for cat in set(c["קטגוריה"] for c in courses if c.get("קטגוריה")):
            if cat in msg:
                topic = cat
                break
        for sub in set(c["תת קטגוריה"] for c in courses if c.get("תת קטגוריה")):
            if sub and sub in msg:
                topic = sub
                break
        if not topic:
            topic = user_state.get("subcategories", [None])[0] or user_state.get("category")
        prompt = msg
        if topic and any(word in msg.lower() for word in salary_keywords):
            prompt = f"מה השכר הממוצע בתחום {topic}?"
        elif topic and any(word in msg.lower() for word in demand_keywords):
            prompt = f"מה הביקוש בתחום {topic} בשוק העבודה בישראל?"

        gpt_reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "ענה בעברית בלבד בקצרה"},
                {"role": "user", "content": prompt}
            ]
        )
        return jsonify({"response": gpt_reply.choices[0].message.content, "options": []})

    # --- ברוך הבא ---
    if stage == "welcome":
        user_state["stage"] = "intro_wait"
        return jsonify({
            "response": "היי! אני צ'אטבוט שמומחה בעזרה לחיילים משוחררים 🎓<br>אני כאן כדי לעזור לך למצוא קורסים שמתאימים בדיוק לך – לפי תחום, אזור ומידע נוסף.<br><br>האם תרצה לנסות? ✨",
            "options": []
        })

    if msg.lower() in ["כן", "יאללה", "בוא נתחיל", "קדימה", "אפשר להתחיל"] and stage == "intro_wait":
        user_state["stage"] = "category"
        response = "מעולה! לפניך מספר שאלות שיעזרו לי למצוא את הקורס המתאים ביותר עבורך ✨<br><br>איזה תחום מעניין אותך?"
        options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
        return jsonify({"response": response, "options": options})

    if msg.lower() in ["לא אהבתי", "אפשר משהו אחר", "תן משהו אחר"]:
        user_state.update({"stage": "category", "category": None, "subcategories": [], "area": None})
        response = "אין בעיה! בוא ננסה שוב למצוא משהו חדש שתאהב 💡<br>מה התחום שמעניין אותך?"
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
                    f"📍 כתובת: {c.get('כתובת', 'לא זמינה')}</div>"
                )
                email = c.get("מייל", "")
                email_link = (
                    f"<a href='mailto:{email}?subject=התעניינות בקורס לחיילים משוחררים"
                    f"&body=שלום, הגעתי אליכם דרך הבוט של הקורסים לחיילים משוחררים ואני מתעניין בקורס. אשמח שתחזרו אליי עם פרטים נוספים. תודה!' target='_blank'>{email or 'לא זמין'}</a>"
                )
                detailed_info[cid] = (
                    f"📞 איש קשר: {c.get('מספר פלאפון', 'לא ידוע')}<br>"
                    f"📧 מייל: {email_link}"
                )

            response = "נמצאו קורסים מתאימים!<br><br>" + "<br><br>".join(preview_lines) + "<br><br>🔍 לחץ על קורס כדי לראות את פרטי הקשר"
            return jsonify({"response": response, "options": [], "details": detailed_info})
        else:
            response = "לא נמצאו קורסים. רוצה שננסה שוב עם תחום אחר?"
            user_state["stage"] = "category"
            options = sorted(set(c["קטגוריה"] for c in courses if c.get("קטגוריה")))
            return jsonify({"response": response, "options": options})

    return jsonify({"response": "שאלה כללית? אני מתמחה בעזרה עם קורסים בלבד 🙂", "options": []})

if __name__ == "__main__":
    app.run(debug=True)
