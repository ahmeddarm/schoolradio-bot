# 🎙️ بوت إذاعة المدرسة

بوت تلغرام لنشر محتوى الإذاعة على GitHub تلقائياً.

## ✨ المميزات

- 📻 نشر سريع بمجرد إرسال المحتوى
- 🔄 استبدال `index.html` في المشروع تلقائياً
- ✅ يعمل على Vercel (Serverless)

## 🚀 التثبيت

### 1. اربط على Vercel
```
https://vercel.com/new
```
اختر هذا المشروع

### 2. أضف Environment Variables
في Vercel → Settings → Environment Variables:
- `BOT_TOKEN`: توكن البوت
- `GITHUB_TOKEN`: GitHub Personal Access Token (مع صلاحية repo)

### 3. إعداد Webhook
بعد رفع المشروع على Vercel:
```
https://your-app.vercel.app/setup?url=https://your-app.vercel.app
```

## 📖 طريقة الاستخدام

| الأمر | الوظيفة |
|-------|---------|
| `/start` | بدء البوت |
| `/update` | نشر محتوى جديد |
| `/cancel` | إلغاء العملية |

### خطوات النشر:
1. أرسل `/update`
2. أدخل اسم الإذاعة
3. الصق محتوى `index.html`
4. سيتم النشر تلقائياً!

## 🔧 الإعدادات

### تغيير المستودع:
عدّل `GITHUB_REPO` في `server.py`:
```python
GITHUB_REPO = "username/repo-name"
```

## 📁 هيكل المشروع

```
├── server.py        # الكود الرئيسي (Flask)
├── vercel.json      # إعدادات Vercel
├── requirements.txt # المتطلبات
└── README.md        # التوثيق
```
