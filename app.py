import json, os, time, threading
from datetime import datetime, timezone, timedelta
from flask import Flask, request, render_template_string
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5001").rstrip("/")
AD_FILE = "hr_knowledge.json"
PORT = int(os.getenv("PORT", "5001"))

GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SYSTEM_PROMPT = """You are ZHRCHumanRightsBot, the official AI assistant of the Zimbabwe Human Rights Commission (ZHRC).
You answer questions related to:
- Human rights (universal, Zimbabwe Constitution Chapter 4 Bill of Rights)
- ZHRC services, offices, management, and procedures
- How to file complaints
- Zimbabwean law related to human rights
- Emergency contacts and support services
- ZHRC leadership and organizational structure
- ZHRC programs, projects, and initiatives
- International human rights frameworks
- Any general knowledge about human rights, governance, and social justice

RULES:
1. Be helpful, accurate, and empathetic
2. Always provide Zimbabwe-specific information when possible
3. If unsure, say so and suggest contacting ZHRC directly
4. For emergencies, always provide emergency numbers (Police: 999)
5. Keep responses concise but informative
6. Auto-detect the user language and respond in the same language (English, Shona, or Ndebele)
7. You may also answer general questions about ZHRC as an organization, its management, staff, programs, and operations
8. If asked about topics completely unrelated to human rights or ZHRC, politely redirect
8. Never provide legal advice - always recommend consulting ZHRC or a lawyer
9. Include relevant contact info when appropriate
10. Be respectful and non-partisan
11. Use your knowledge of human rights, Zimbabwe, and ZHRC to provide comprehensive answers"""

# ---- State ----
user_lang = {}
chat_history = {}

def load_kb():
    with open(AD_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_time_greeting():
    tz = timezone(timedelta(hours=2))
    hour = datetime.now(tz).hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

def get_lang(user_id):
    return user_lang.get(user_id, "en")

LANG_NAMES = {"en": "English", "sn": "Shona", "nd": "Ndebele"}

def call_gemini(prompt):
    """Call Gemini REST API. Returns text or None on failure."""
    if not GEMINI_API_KEY:
        return None
    try:
        url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 500}
        }
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            data = r.json()
            return data['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            print(f"Gemini API error: {r.status_code} {r.text[:200]}")
            return None
    except Exception as e:
        print(f"Gemini exception: {e}")
        return None

def handle_message(user_id, text):
    """Core bot logic. Returns list of reply strings."""
    replies = []
    text = text.strip()
    text_lower = text.lower()
    kb = load_kb()
    lang = get_lang(user_id)

    # Language selection
    if text_lower in ["language", "lang", "mutauro", "ulimi"]:
        replies.append("Select your language / Sarudza mutauro wako / Khetha ulimi lwakho:\n\n1. Type 'english' for English\n2. Type 'shona' for Shona\n3. Type 'ndebele' for Ndebele")
        return replies

    if text_lower in ["english", "en"]:
        user_lang[user_id] = "en"
        replies.append("Language changed to English. Type 'hie' to start.")
        return replies
    if text_lower in ["shona", "sn"]:
        user_lang[user_id] = "sn"
        replies.append("Mutauro wachinjirwa kuShona. Nyora 'hie' kuti utange.")
        return replies
    if text_lower in ["ndebele", "nd", "isindebele"]:
        user_lang[user_id] = "nd"
        replies.append("Ulimi lushintshiwe lube isiNdebele. Bhala 'hie' ukuze uqale.")
        return replies

    # Greeting
    if text_lower in ["hie", "hi", "hello", "hey", "mhoro", "sawubona", "greetings", "howzit"]:
        time_greet = get_time_greeting()
        replies.append(time_greet + "! I am ZHRCBOT. How can I help you today?")
        return replies

    # Structured commands (quick access)
    if text_lower in ["rights", "kodzero", "amalungelo", "human rights", "my rights"]:
        replies.append(kb["rights"][lang])
        return replies

    if text_lower in ["complaint", "nyaya", "isikhalazo", "file complaint", "report"]:
        replies.append(kb["complaint"][lang])
        return replies

    if text_lower in ["services", "zvinonzi", "okwenziwa", "what does zhrc do", "zhrc"]:
        replies.append(kb["services"][lang])
        return replies

    if text_lower in ["offices", "maofisi", "amahhovisi", "locations", "where", "address"]:
        replies.append(kb["offices"][lang])
        return replies

    if text_lower in ["organization", "org", "management", "leadership", "about", "about zhrc", "info"]:
        replies.append(kb.get("organization", {}).get(lang, kb["services"][lang]))
        return replies

    if text_lower in ["emergency", "ngozi", "iphuthumayo", "urgent", "danger"]:
        replies.append(kb["emergency"][lang])
        return replies

    if text_lower in ["documents", "magwaro", "amadokhumenti", "download", "guides", "pdf"]:
        replies.append(kb["documents"][lang])
        return replies

    if text_lower in ["faq", "questions", "mibvunzo", "imibuzo"]:
        replies.append(kb["faq"][lang])
        return replies

    # Generative AI response for open-ended questions
    context = (kb["rights"][lang] + "\n\n" + kb["services"][lang] + "\n\n" + kb["complaint"][lang]
              + "\n\n" + kb["offices"][lang] + "\n\n" + kb["faq"][lang]
              + "\n\n" + kb.get("organization", {}).get(lang, ""))
    history = chat_history.get(user_id, [])
    history_text = ""
    for h in history[-3:]:
        history_text += f"User: {h[0]}\nBot: {h[1]}\n"

    prompt = f"""Knowledge base context:
{context}

Previous conversation:
{history_text}

User question: {text}

Detect the language of the user question and respond in that same language (English, Shona, or Ndebele). Be helpful, accurate, and concise. If the question is not about human rights, politely redirect. Include relevant contact info when appropriate."""

    reply = call_gemini(prompt)
    if reply:
        if user_id not in chat_history:
            chat_history[user_id] = []
        chat_history[user_id].append((text, reply))
        chat_history[user_id] = chat_history[user_id][-10:]
        replies.append(reply)
    else:
        replies.append(kb["unknown"][lang])
    return replies

# ---- Web Chat API ----
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "web_user")
    text = data.get("message", "")
    replies = handle_message(user_id, text)
    return {"replies": replies}, 200

# ---- Web Chat UI ----
@app.route("/", methods=["GET"])
@app.route("/test", methods=["GET"])
def test_ui():
    return render_template_string(CHAT_HTML)

CHAT_HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ZHRCHumanRightsBot - AI Chat</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #1a3a2e 0%, #0f5132 50%, #198754 100%); display: flex; justify-content: center; align-items: center; height: 100vh; }
  .chat-container { width: 480px; max-width: 100%; height: 95vh; background: #fff; border-radius: 16px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); display: flex; flex-direction: column; overflow: hidden; }
  .chat-header { background: linear-gradient(135deg, #198754, #157347); color: #fff; padding: 18px 20px; display: flex; align-items: center; gap: 14px; }
  .chat-header .avatar { width: 48px; height: 48px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 24px; border: 2px solid rgba(255,255,255,0.3); }
  .chat-header .info h3 { font-size: 18px; font-weight: 600; }
  .chat-header .info p { font-size: 12px; opacity: 0.85; margin-top: 2px; }
  .chat-messages { flex: 1; padding: 20px; overflow-y: auto; background: #f0f5f0; display: flex; flex-direction: column; gap: 10px; }
  .msg { max-width: 90%; padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; animation: fadeIn 0.2s ease; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  .msg.user { align-self: flex-end; background: #d1e7dd; border-bottom-right-radius: 4px; }
  .msg.bot { align-self: flex-start; background: #fff; border-bottom-left-radius: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
  .msg a { color: #198754; text-decoration: none; font-weight: 600; }
  .chat-input { display: flex; padding: 12px 16px; background: #fff; gap: 10px; border-top: 1px solid #e0e0e0; }
  .chat-input input { flex: 1; padding: 12px 18px; border: 2px solid #e0e0e0; border-radius: 24px; font-size: 14px; outline: none; transition: border-color 0.2s; }
  .chat-input input:focus { border-color: #198754; }
  .chat-input button { background: linear-gradient(135deg, #198754, #157347); color: #fff; border: none; border-radius: 50%; width: 44px; height: 44px; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; transition: transform 0.1s; }
  .chat-input button:hover { transform: scale(1.05); }
  .typing { align-self: flex-start; background: #fff; padding: 12px 16px; border-radius: 12px; font-size: 12px; color: #888; font-style: italic; border-bottom-left-radius: 4px; }
  .footer { text-align: center; padding: 6px; font-size: 10px; color: #999; background: #f0f5f0; }
  .quick-btns { display: flex; gap: 6px; padding: 8px 12px; background: #f0f5f0; flex-wrap: wrap; justify-content: center; }
  .quick-btns button { background: #fff; border: 1px solid #ccc; border-radius: 16px; padding: 6px 12px; font-size: 12px; cursor: pointer; transition: background 0.2s; }
  .quick-btns button:hover { background: #d1e7dd; }
  .ai-badge { display: inline-block; background: #198754; color: #fff; font-size: 10px; padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
</style>
</head>
<body>
<div class="chat-container">
  <div class="chat-header">
    <div class="avatar">⚖️</div>
    <div class="info">
      <h3>ZHRCBOT</h3>
      <p>Zimbabwe Human Rights Commission</p>
    </div>
  </div>
  <div class="chat-messages" id="messages"></div>

  <div class="chat-input">
    <input type="text" id="input" placeholder="Ask anything about human rights..." onkeypress="if(event.key==='Enter')sendMessage()" autofocus>
    <button onclick="sendMessage()">➤</button>
  </div>
  <div class="footer">Zimbabwe Human Rights Commission</div>
</div>
<script>
  const userId = "web_user_" + Math.random().toString(36).substr(2, 9);
  const messagesDiv = document.getElementById('messages');
  const input = document.getElementById('input');

  function addMsg(text, isUser) {
    const div = document.createElement('div');
    div.className = 'msg ' + (isUser ? 'user' : 'bot');
    let html = text.replace(/(https?:\/\/[^\s]+)/g, function(url) {
      return '<a href="' + url + '" target="_blank">🔗 Open Link</a>';
    });
    div.innerHTML = html;
    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    addMsg(text, true);
    input.value = '';
    const typing = document.createElement('div');
    typing.className = 'typing';
    typing.textContent = 'ZHRCBOT is thinking...';
    messagesDiv.appendChild(typing);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, message: text })
      });
      const data = await res.json();
      typing.remove();
      for (const reply of data.replies) {
        addMsg(reply, false);
      }
    } catch (e) {
      typing.remove();
      addMsg('Error: ' + e.message, false);
    }
  }

  function sendQuick(text) {
    input.value = text;
    sendMessage();
  }

  setTimeout(() => {
    addMsg("Hie! I am ZHRCBOT. How can I help you today?", false);
  }, 500);
</script>
</body>
</html>'''

# ---- Admin status ----
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "zhrcaidesk_admin_123")

@app.route("/admin/status", methods=["GET"])
def admin_status():
    if request.args.get("secret") != ADMIN_SECRET:
        return "Unauthorized", 403
    return "OK - ZHRCHumanRightsBot AI is running", 200

if __name__ == "__main__":
    app.run(port=PORT, debug=True)
