#!/usr/bin/env python3
"""
بوت إذاعة المدرسة - Telegram Bot (Vercel Serverless)
ينشر على GitHub: ahmeddarm/SchoolRadio
"""
import os
import io
import json
import base64
import logging
import requests
from flask import Flask, request, jsonify

# ─── الإعدادات ──────────────────────────────────────────────────────────────── #
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8733216596:AAHLzEokx8d1ozuA0Ao7G4yM-m6qEu5ESq4")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
GITHUB_REPO = "ahmeddarm/SchoolRadio"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

app = Flask(__name__)
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  حالة المستخدم (في الذاكرة - تستخدم GitHub API)
# ═══════════════════════════════════════════════════════════════════════════════
_user_states: dict[int, dict] = {}

# ═══════════════════════════════════════════════════════════════════════════════
#  أوامر تلغرام المساعدة
# ═══════════════════════════════════════════════════════════════════════════════
def tg_send_message(chat_id, text, parse_mode="Markdown"):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=10
    )

def tg_delete_message(chat_id, message_id):
    requests.post(
        f"{TELEGRAM_API}/deleteMessage",
        json={"chat_id": chat_id, "message_id": message_id},
        timeout=10
    )

def tg_get_me():
    try:
        resp = requests.get(f"{TELEGRAM_API}/getMe", timeout=5).json()
        if resp.get("ok"):
            return resp["result"]
    except Exception:
        pass
    return None

# ═══════════════════════════════════════════════════════════════════════════════
#  GitHub API - النشر
# ═══════════════════════════════════════════════════════════════════════════════
def get_file_sha(repo, path):
    """جلب SHA للملف إذا موجود"""
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("sha")
    except Exception as e:
        logger.warning(f"Error getting SHA: {e}")
    return None

def deploy_to_github(broadcast_name: str, html_content: str) -> tuple[bool, str]:
    """ينشر المحتوى على GitHub"""
    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        path = "index.html"
        sha = get_file_sha(GITHUB_REPO, path)

        content = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")

        data = {
            "message": f"تحديث إذاعة: {broadcast_name}",
            "content": content,
        }
        if sha:
            data["sha"] = sha

        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        resp = requests.put(url, headers=headers, json=data, timeout=30)

        if resp.status_code in [200, 201]:
            return True, "تم النشر بنجاح!"
        else:
            error_msg = resp.json().get("message", "خطأ غير معروف")
            return False, f"خطأ GitHub: {error_msg}"

    except Exception as e:
        logger.exception("Deploy failed")
        return False, str(e)

# ═══════════════════════════════════════════════════════════════════════════════
#  معالجات الأوامر
# ═══════════════════════════════════════════════════════════════════════════════
def handle_start(chat_id):
    text = (
        "🎙️ *مرحباً بك في بوت إذاعة المدرسة!*\n\n"
        "📌 *طريقة الاستخدام:*\n\n"
        "1️⃣ أرسل /update لبدء النشر\n\n"
        "2️⃣ أدخل اسم الإذاعة\n\n"
        "3️⃣ الصق محتوى index.html\n\n"
        "📡 سيتم نشره تلقائياً على:\n"
        "`ahmeddarm/SchoolRadio`\n\n"
        "⚙️ *أوامر:*\n"
        "/start - بدء\n"
        "/update - نشر محتوى جديد"
    )
    tg_send_message(chat_id, text)

def handle_update(chat_id, user_id):
    """طلب اسم الإذاعة"""
    _user_states[user_id] = {"step": "waiting_name"}
    text = (
        "📻 *أدخل اسم الإذاعة:*\n\n"
        "مثال: إذاعة اليوم الوطني, إذاعة الختام..."
    )
    tg_send_message(chat_id, text)

def handle_cancel(chat_id, user_id):
    """إلغاء العملية"""
    if user_id in _user_states:
        del _user_states[user_id]
    tg_send_message(chat_id, "❌ تم الإلغاء.")

def handle_broadcast_name(chat_id, user_id, name):
    """استلام اسم الإذاعة"""
    if name.lower() == "إلغاء":
        handle_cancel(chat_id, user_id)
        return

    if len(name) < 2:
        tg_send_message(chat_id, "❌ الاسم قصير جداً. حاول مرة أخرى:")
        return

    _user_states[user_id] = {
        "step": "waiting_html",
        "broadcast_name": name.strip()
    }
    text = (
        f"✅ تم.\n\n"
        f"📻 الإذاعة: *{name.strip()}*\n\n"
        f"📄 الآن أرسل محتوى ملف index.html\n"
        f"(الصق الكود كاملاً)\n\n"
        f"❌ للإلغاء أرسل: إلغاء"
    )
    tg_send_message(chat_id, text)

def handle_html_content(chat_id, user_id, html_content, message_id):
    """استلام HTML ونشره"""
    if html_content.strip() == "إلغاء":
        handle_cancel(chat_id, user_id)
        return

    state = _user_states.get(user_id, {})
    broadcast_name = state.get("broadcast_name", "إذاعة عامة")

    # حذف رسالة المستخدم (لحماية المحتوى)
    tg_delete_message(chat_id, message_id)

    tg_send_message(chat_id, "⏳ جاري النشر...")

    # النشر
    success, msg = deploy_to_github(broadcast_name, html_content)

    if success:
        tg_send_message(
            chat_id,
            f"✅ *تم النشر بنجاح!*\n\n"
            f"📻 الإذاعة: {broadcast_name}\n"
            f"🔗 github.com/{GITHUB_REPO}\n\n"
            f"⏳ انتظر دقائق حتى يظهر التحديث على الموقع."
        )
    else:
        tg_send_message(
            chat_id,
            f"❌ *حدث خطأ أثناء النشر*\n\n"
            f"{msg}\n\n"
            f"📌 تأكد من:\n"
            f"• صلاحية الـ GitHub Token\n"
            f"• صلاحية الوصول للمشروع\n\n"
            f"أرسل /update للمحاولة مرة أخرى"
        )

    # تنظيف الحالة
    if user_id in _user_states:
        del _user_states[user_id]

# ═══════════════════════════════════════════════════════════════════════════════
#  Flask Routes
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    bot_info = tg_get_me()
    return jsonify({
        "status": "ok",
        "bot": bot_info.get("username") if bot_info else None
    })

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False}), 400

    message = data.get("message")
    if not message:
        return jsonify({"ok": True})

    chat_id = message["chat"]["id"]
    user_id = message.get("from", {}).get("id", chat_id)
    text = message.get("text", "").strip()
    message_id = message.get("message_id")

    if not text:
        return jsonify({"ok": True})

    # الأوامر
    if text.startswith("/start"):
        handle_start(chat_id)
    elif text.startswith("/update"):
        handle_update(chat_id, user_id)
    elif text.startswith("/cancel"):
        handle_cancel(chat_id, user_id)
    elif user_id in _user_states:
        state = _user_states[user_id]
        if state.get("step") == "waiting_name":
            handle_broadcast_name(chat_id, user_id, text)
        elif state.get("step") == "waiting_html":
            handle_html_content(chat_id, user_id, text, message_id)
    else:
        tg_send_message(chat_id, "❓ أرسل /start أو /update")

    return jsonify({"ok": True})

@app.route("/setup")
def setup_webhook():
    """إعداد Webhook"""
    public_url = request.args.get("url")
    if not public_url:
        return jsonify({
            "error": "Pass ?url=YOUR_PUBLIC_URL",
            "example": "/setup?url=https://your-app.vercel.app"
        }), 400

    webhook_url = f"{public_url.rstrip('/')}/webhook"
    resp = requests.post(
        f"{TELEGRAM_API}/setWebhook",
        json={"url": webhook_url, "allowed_updates": ["message"]},
        timeout=10
    ).json()

    return jsonify({
        "telegram_response": resp,
        "webhook_url": webhook_url
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ═══════════════════════════════════════════════════════════════════════════════
#  تشغيل محلي
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("🚀 Starting server on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=True)
