"""
بوت تلغرام لإدارة إذاعة المدرسة
- يولّد SSH keys ثابتة لكل مستخدم
- ينشر على GitHub عند طلب Update
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, CallbackContext, filters
)
from github import Github
import paramiko
from pathlib import Path

# ========== الإعدادات ==========
BOT_TOKEN = "8733216596:AAHLzEokx8d1ozuA0Ao7G4yM-m6qEu5ESq4"
GITHUB_REPO = "ahmeddarm/SchoolRadio"
KEYS_DIR = Path("keys")
KEYS_DIR.mkdir(exist_ok=True)

# ========== حالات المحادثة ==========
WAITING_BROADCAST_NAME, WAITING_HTML_CONTENT = range(2)

# ========== إعداد السجلات ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== قاعدة البيانات البسيطة ==========
USERS_FILE = Path("users.json")

def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

# ========== توليد SSH Keys ==========
def generate_ssh_key(user_id: int) -> tuple[str, str]:
    """يولّد SSH key للمستخدم ويجيب الـ public و private keys"""
    key_path = KEYS_DIR / str(user_id)
    
    # إذا المفتاح موجود، رجعه
    if key_path.exists():
        with open(key_path, 'r') as f:
            private_key = f.read()
        with open(f"{key_path}.pub", 'r') as f:
            public_key = f.read()
        return private_key, public_key
    
    # توليد مفتاح جديد
    key = paramiko.RSAKey.generate(2048)
    key.write_private_key_file(str(key_path))
    
    with open(f"{key_path}.pub", 'w') as f:
        f.write(f"{key.get_name()} {key.get_base64()}")
    
    private_key = key_path.read_text()
    public_key = f"{key_path}.pub".read_text()
    
    return private_key, public_key

# ========== النشر على GitHub ==========
def deploy_to_github(broadcast_name: str, html_content: str, private_key: str) -> bool:
    """ينشر المحتوى على GitHub"""
    try:
        # إنشاء SSH key مؤقت
        temp_key = KEYS_DIR / "temp_key"
        with open(temp_key, 'w') as f:
            f.write(private_key)
        os.chmod(temp_key, 0o600)
        
        # إعداد SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # الاتصال بـ GitHub عبر SSH
        stdin, stdout, stderr = ssh.exec_command(
            f"git clone git@github.com:{GITHUB_REPO}.git /tmp/schoolradio"
        )
        
        # إذا الفولدر موجود، مجرد pull
        if os.path.exists("/tmp/schoolradio"):
            os.system("cd /tmp/schoolradio && git pull origin main 2>/dev/null")
        else:
            try:
                ssh.connect(
                    hostname="github.com",
                    username="git",
                    key_filename=str(temp_key),
                    timeout=10
                )
            except:
                pass
        
        # كتابة الملف الجديد
        index_path = "/tmp/schoolradio/index.html"
        if os.path.exists("/tmp/schoolradio"):
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Commit و Push
            os.system(f'''
                cd /tmp/schoolradio && 
                git config user.email "bot@schoolradio.com" &&
                git config user.name "SchoolRadio Bot" &&
                git add index.html &&
                git commit -m "تحديث إذاعة: {broadcast_name}" &&
                git push origin main
            ''')
        
        # تنظيف
        if temp_key.exists():
            os.remove(temp_key)
        
        return True
        
    except Exception as e:
        logger.error(f"خطأ في النشر: {e}")
        return False

# ========== أوامر البوت ==========
async def start(update: Update, context: CallbackContext):
    """الأمر /start - يولّد SSH key للمستخدم"""
    user_id = update.effective_user.id
    users = load_users()
    
    # التحقق إذا المستخدم جديد
    if str(user_id) not in users:
        # توليد SSH key
        private_key, public_key = generate_ssh_key(user_id)
        
        # حفظ بيانات المستخدم
        users[str(user_id)] = {
            "username": update.effective_user.username,
            "created_at": datetime.now().isoformat()
        }
        save_users(users)
        
        # رسالة الترحيب مع SSH key
        welcome_message = """
🎙️ *مرحباً بك في بوت إذاعة المدرسة!*

تم توليد مفتاح SSH خاص بك:
─────────────────────
```
{public_key}
```
─────────────────────

📋 *الخطوات التالية:*
1️⃣ انسخ الـ SSH Key أعلاه
2️⃣ اذهب إلى GitHub → Settings → SSH Keys
3️⃣ أضف المفتاح الجديد

⚠️ *ملاحظة:* هذا المفتاح ثابت - لا تحذفه!

بمجرد إضافة المفتاح، أرسل /help للمساعدة
        """.format(public_key=public_key.strip())
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "👋 *أهلاً بعودتك!*\n\n"
            "لديك مفتاح SSH مسجل.\n"
            "للنشر، أرسل /update",
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: CallbackContext):
    """الأمر /help"""
    help_text = """
📚 *أوامر البوت:*

/start - بدء البوت وتوليد SSH Key
/update - نشر محتوى جديد
/help - عرض المساعدة
/key - إعادة عرض الـ SSH Key
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def show_key(update: Update, context: CallbackContext):
    """الأمر /key - يعرض SSH key للمستخدم"""
    user_id = update.effective_user.id
    
    try:
        key_path = KEYS_DIR / str(user_id)
        if key_path.exists():
            public_key = (f"{key_path}.pub").read_text().strip()
            await update.message.reply_text(
                f"🔑 *مفتاح SSH الخاص بك:*\n\n```\n{public_key}\n```",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ لا يوجد مفتاح. أرسل /start أولاً"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

async def update_command(update: Update, context: CallbackContext):
    """الأمر /update - يبدأ عملية النشر"""
    user_id = update.effective_user.id
    
    # التحقق من وجود SSH key
    key_path = KEYS_DIR / str(user_id)
    if not key_path.exists():
        await update.message.reply_text(
            "❌ لا يوجد مفتاح SSH!\n"
            "أرسل /start أولاً لتوليد المفتاح."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📻 *أدخل اسم الإذاعة:*\n\n"
        "مثال: إذاعة اليوم الأول, إذاعة الختام, إلخ...",
        parse_mode='Markdown'
    )
    return WAITING_BROADCAST_NAME

async def receive_broadcast_name(update: Update, context: CallbackContext):
    """استلام اسم الإذاعة"""
    broadcast_name = update.message.text.strip()
    
    if len(broadcast_name) < 2:
        await update.message.reply_text("❌ الاسم قصير جداً. حاول مرة أخرى:")
        return WAITING_BROADCAST_NAME
    
    context.user_data['broadcast_name'] = broadcast_name
    
    await update.message.reply_text(
        f"✅ تم.\n\n"
        f"📻 الإذاعة: *{broadcast_name}*\n\n"
        f"📄 الآن أرسل محتوى ملف index.html\n"
        f"(الصق الكود كاملاً)",
        parse_mode='Markdown'
    )
    return WAITING_HTML_CONTENT

async def receive_html_content(update: Update, context: CallbackContext):
    """استلام محتوى HTML ونشره"""
    user_id = update.effective_user.id
    broadcast_name = context.user_data.get('broadcast_name', 'إذاعة عامة')
    html_content = update.message.text
    
    # التحقق من HTML
    if '<html' not in html_content.lower() and '<!doctype' not in html_content.lower():
        await update.message.reply_text(
            "⚠️ يبدو أن هذا ليس ملف HTML.\n"
            "هل تريد المتابعة؟ (نعم/لا)"
        )
        context.user_data['pending_html'] = html_content
        # نكمل رغم ذلك
        pass
    
    await update.message.reply_text("⏳ جاري النشر...")
    
    # جلب الـ private key
    key_path = KEYS_DIR / str(user_id)
    private_key = key_path.read_text()
    
    # النشر
    success = deploy_to_github(broadcast_name, html_content, private_key)
    
    if success:
        await update.message.reply_text(
            f"✅ *تم النشر بنجاح!*\n\n"
            f"📻 الإذاعة: {broadcast_name}\n"
            f"🔗 Repo: github.com/{GITHUB_REPO}\n\n"
            f"يمكن التحقق من الموقع بعد دقائق.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء النشر.\n"
            "تأكد من:\n"
            "• إضافة الـ SSH Key إلى GitHub\n"
            "• صلاحية الوصول للمشروع\n\n"
            "حاول مرة أخرى بـ /update"
        )
    
    # تنظيف البيانات المؤقتة
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext):
    """إلغاء العملية"""
    await update.message.reply_text("❌ تم الإلغاء.")
    context.user_data.clear()
    return ConversationHandler.END

# ========== تشغيل البوت ==========
def main():
    """الدالة الرئيسية"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("key", show_key))
    
    # محادثة Update
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("update", update_command)],
        states={
            WAITING_BROADCAST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_name)
            ],
            WAITING_HTML_CONTENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_html_content)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    
    # تشغيل
    print("🤖 البوت يعمل...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
