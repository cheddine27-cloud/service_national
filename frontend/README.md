# التشغيل — المعاينة في المتصفح (المرحلة 3)

المعادن: المعاينة يعمل **بدون إنترنت** بعد تثبيت التبعيات مرة واحدة.

## 1) الخادم الخلفي (FastAPI)

```powershell
cd F:\main\service_national

# استخدم قاعدة بيانات تطوير آمنة (لا تلتمس قاعدة الإنتاج):
$env:NS_MODE = "dev"
$env:NS_DB_PATH = "F:\main\service_national\data\dev_preview.db"
& "C:\Program Files\Odoo 17.0.20260103\python\python.exe" server.py
```

الخادم يبدأ على `http://127.0.0.1:8765` — وتوجد وثائق التفاعل على `/docs`.
أوصاف الإنتاج: انظر `PHASE2` notes (NS_CONFIRM_PRODUCTION=1).

## 2) الواجهة (Vite)

```powershell
cd F:\main\service_national\frontend
npm install          # مرة واحدة فقط
npm run dev
```

ثم افتح في المتصفح: **http://localhost:5173**

## 3) ملاحظات مهمة

- الطرفية عبر الـ proxy في `vite.config.ts` — أي نداء `/api/*` يعود إلى `127.0.0.1:8765`، بلا مشاكل CORS.
- `VITE_API_BASE` (اختياري في `.env.local`): تحديد مباشر مثل `http://127.0.0.1:8765/api` — جد injira مستقبلي Tauri دون إعادة كتابة.
- `VITE_USE_MOCK=1` **غير مفعل افتراضيًا**؛ فقط إن أردت التجريب you DO NOT want mock in production data — وضع MOCK محول للمحاكاة المحلية فقط.
- الخطوط (Tajawal) مرفوعة محليًا في `public/fonts` — بلا إنترنت.
- لا يعمل النظام على شبكة عامة — الواجهة فقط محلية.

## 4) تطبيق Tkinter القديم

يبقى يعمل كما هو على نفس قاعدة البيانات:

```powershell
& "C:\Program Files\Odoo 17.0.20260103\python\python.exe" main.py
```
