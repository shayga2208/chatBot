async function sendMessage(fromButton = null) {
  const input = document.getElementById("userInput");
  const text = fromButton || input.value.trim();
  if (!text && fromButton === null) return;

  if (text) addMessage("user", text);
  if (fromButton === null) input.value = "";
  document.getElementById("options").innerHTML = "";

  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text })
  });

  const data = await res.json();
  addMessage("bot", data.response);

  if (data.details) {
    window.courseDetails = data.details;
  }

  if (data.options.length > 0) {
    const optionsBox = document.getElementById("options");
    data.options.forEach(opt => {
      const btn = document.createElement("button");
      btn.innerText = opt;
      btn.onclick = () => sendMessage(opt);
      optionsBox.appendChild(btn);
    });
    scrollToBottom();
  }
}

function addMessage(sender, text) {
  const div = document.createElement("div");
  div.className = `msg ${sender}`;
  div.innerHTML = text;
  document.getElementById("messages").appendChild(div);
  scrollToBottom();
}

function scrollToBottom() {
  const container = document.getElementById("messages");
  container.scrollTop = container.scrollHeight;
}

function fetchCourseDetails(courseId) {
  if (!window.courseDetails || !window.courseDetails[courseId]) return;

  const detailDiv = document.createElement("div");
  detailDiv.className = "msg bot";
  detailDiv.innerHTML = window.courseDetails[courseId];
  document.getElementById("messages").appendChild(detailDiv);
  scrollToBottom();

  const summary = document.createElement("div");
  summary.className = "msg bot";
  summary.innerHTML = "📬 לסיכום: תוכל ללחוץ על כתובת המייל כדי לשלוח פנייה אוטומטית ✉️<br>שמחתי לעזור! אני כאן לכל שאלה נוספת 😊";
  setTimeout(() => {
    document.getElementById("messages").appendChild(summary);
    scrollToBottom();
  }, 300);
}

async function resetChat() {
  document.getElementById("messages").innerHTML = "";
  document.getElementById("options").innerHTML = "";
  const res = await fetch("/reset", { method: "POST" });
  const data = await res.json();
  addMessage("bot", data.response);
}

window.onload = () => {
  const firstMessage = `היי! אני צ'אטבוט שמומחה בעזרה לחיילים משוחררים 🎓<br>
אני כאן כדי לעזור לך למצוא קורסים שמתאימים בדיוק לך – לפי תחום, אזור ומידע נוסף.<br><br>
האם תרצה לנסות? ✨`;
  addMessage("bot", firstMessage);
};
