# ملخص جلسة العمل — نظام الخدمة الوطنية

## 1. الهدف
برنامج سطح مكتب (Windows) يعمل **بدون إنترنت**، يخزن البيانات **محلياً** (SQLite)، لإدارة بيانات الطلاب + جداول الخدمات (الخدمة الوطنية). يولد قوائم أسبوعية (PDF) مع توقيعات وتاريخ/يوم.

## 2. التقنية
- Python 3.12 (Odoo bundled) + Tkinter (RTL/عربي)
- SQLite (محلي)
- ReportLab (PDF عربي مع arabic-reshaper + python-bidi)
- تشغيل: `run.bat` → `main.py`
- مسار Python: `C:\Program Files\Odoo 17.0.20260103\python\python.exe`

## 3. هيكل المشروع (E:\service_national)
- `main.py` — نقطة التشغيل (يحدد DB في `data\`)
- `db.py` — قاعدة البيانات (SQLite) + CRUD
- `scheduler.py` — خوارزمية التوليد الأسبوعي
- `reports.py` — توليد PDF (حراسة/مطعم/مطبخ/تنظيف/مرحاض/اختيارية/طلاب)
- `ui.py` — واجهة Tkinter (5 شاشات)
- `run.bat` — تشغيل
- `README.txt` — تعليمات
- `requirements.txt` — الحزم
- `.gitignore` — استثناءات
- `SESSION_SUMMARY.md` — هذا الملف
- `data\` — قاعدة البيانات (غير مرفوعة في Git)

## 4. بنية البيانات
### groups
- A (فوج أ), B (فوج ب)

### squads
- 5 في كل مجموعة → 10 أفواج (A1..A5, B1..B5)

### students
- full_name, father_name, national_id, birth_date, phone, address, blood_type, rank, enlistment_date, notes, squad_id

### weeks
- start_date, end_date, created_at, notes

### assignments
- week_id, day_index (0..6), date, service (guard/restaurant/kitchen/cleaning/toilet), squad_id, count, notes

### optional_services
- week_id, date, name, count, receiver, squad_id, notes, created_at

### settings
- unit_name, toilet_daily_count (افتراضي 3), guard_daily_count (افتراضي 4), week_start

## 5. خوارزمية التوليد (scheduler.generate_week)
- مدخلات: start_date (YYYY-MM-DD), toilet_count, guard_count
- 7 أيام:
  1. حراسة: اختيار فوج (الأقل استخداماً)
  2. مطعم: ≠ حراسة
  3. مطبخ: ≠ حراسة/مطعم
  4. تنظيف: ≠ حراسة (يفضل ≠ مطعم/مطبخ)
  5. مرحاض: فوج واحد للأسبوع + count يومي
- توزيع عادل (round-robin حسب الاستخدام)
- الفوج في الحراسة لا يعمل مطعم/مطبخ

## 6. شاشات UI
1. **لوحة التحكم**: إحصائيات + إنشاء أفواج + طباعة الطلاب
2. **الأفواج والطلاب**: إضافة/تعديل/حذف، فلتر، طباعة
3. **الخدمات الاختيارية**: إضافة/حذف + طباعة
4. **الجداول الأسبوعية**: توليد، اختيار أسبوع، تعديل تعيين، طباعة (PDF/مباشر)
5. **الإعدادات**: اسم الوحدة، عدد افتراضي للمرحاض/الحراسة، مسار DB

## 7. الطباعة (reports.py)
- PDF عربي RTL (Tahoma)
- رأس: اسم الوحدة، عنوان، أسبوع، تاريخ التوليد
- جدول (حسب الخدمة)
- تذييل: توقيعات (مسؤول/مستلم/قائد فوج/قائد وحدة) + تاريخ
- فتح PDF or طباعة مباشرة (os.startfile)

## 8. إجابات المستخدم (قرارات)
- بداية الأسبوع: **السبت**
- عدد المرحاض يومياً: **3** (قابل للتعديل)
- عدد الحراسة يومياً: **4** (قابل للتعديل)
- Guard: حسب الفوج + عدد
- DB: **بجانب البرنامج** (E:\service_national\data\)
- التعيينات: **قابلة للتعديل** (يدوي)
- رفع في GitHub: نعم

## 9. GitHub
- المستودع: https://github.com/cheddine27-cloud/service_national
- الفرع: main
- Commit: "Initial commit: National Service schedule app"
- .gitignore: data/*.db, __pycache__, *.pdf
- remote origin (محلي): https://github.com/cheddine27-cloud/service_national.git

## 10. اختصارات/تشغيل
- اختصار سطح المكتب: `NationalService.lnk` → `E:\service_national\run.bat`
- Python: `C:\Program Files\Odoo 17.0.20260103\python\python.exe`

## 11. points d'arrêt / suivants possibles
- إضافة حقول للطلاب (تم)
- إضافة GitHub Actions (未 fait, optionnel)
- تحسين UI (scroll في dialog الطالب)
- export/backup DB
- إضافة "قائد الفوج" في طباعة الاختيارية (تم)

## 12. commandes utiles
```bash
# تشغيل
E:\service_national\run.bat

# تثبيت حزم (إذا لزم)
pip install -r requirements.txt

# Git
cd E:\service_national
git status
git add .
git commit -m "..."
git push
```

## 13. ملاحظة
هذا الملف يلخص الجلسة. لإعادة الإرسال لاحقاً، ارفعه وأرسله، وسأعرف أين توقفنا.
