# PHASE 1 — مراجعة وخطة التحول إلى React
# National Service — Audit & Migration Design Plan

> **ملاحظة ميدانية:** المسار `E:\service_national` غير موجود حالياً على هذا الجهاز. النسخة الفعالة المراجَعة هي نسخة مستنسخة من GitHub في `F:\main\service_national`. قبل التنفيذ يجب التأكد من المسار الذي يحتوي قاعدة البيانات الحقيقية `data\service_national.db`.

---

## A. تقرير معمارية المشروع الحالي (Audit)

### A.1 المكونات

| الملف | الحجم | الدور الفعلي (بعد قراءة الكود) |
|---|---|---|
| `main.py` | 31 سطر | `NS_DB_PATH` ← `data/service_national.db`، `db.init_db()`، `ensure_default_squads`، فتح `App(conn)` |
| `db.py` | 344 سطر | SCHEMA كامل + CRUD لكل الجداول + إعدادات + ترحيل أعمدة قديمة (ALTER TABLE للطلاب) |
| `scheduler.py` | 71 سطر | `generate_week()` — 7 أيام × 5 خدمات، توزيع عادل |
| `reports.py` | ~330 سطر | 7 مولدات PDF عربية (ReportLab + reshaper + bidi) |
| `ui.py` | ~710 سطر | `App(tk.Tk)` + 5 إطارات: Dashboard, Squads, Optional, Weekly, Settings |
| `run.bat` | 145 B | تشغيل بهاتف Python المضمّن في Odoo |

### A.2 مخطط قاعدة البيانات (من SCHEMA فعلي)

- `settings(key PK, value)` — مفاتيح: `unit_name`, `toilet_daily_count=3`, `guard_daily_count=4`, `week_start=Saturday`
- `groups(id, code UNIQUE, name)` — A/B تُزرع تلقائياً
- `squads(id, group_id→groups CASCADE, number, name, size=0, UNIQUE(group_id,number))`
- `students(id, squad_id→squads SET NULL, full_name, father_name, national_id, birth_date, phone, address, blood_type, rank, enlistment_date, notes, created_at)`
- `weeks(id, start_date, end_date, created_at, notes)`
- `assignments(id, week_id→weeks CASCADE, day_index 0..6, date, service, squad_id SET NULL, count, notes, UNIQUE(week_id, day_index, service))`
- `optional_services(id, week_id SET NULL, date, name, count, receiver, squad_id, notes, created_at)`

ملاحظات:
- `day_index` يبدأ من 0 يوم **السبت**؟ في الواقع الكود يستخدم `start_date + d` مباشرة، و daytime names في `db.DAY_NAMES_AR` تبدأ من الاثنين — لكن `scheduler` يولّد 7 أيام متتالية من التاريخ المُعطى (المستخدم يختار السبت كبداية). يجب توحيد هذا في الواجهة الجديدة.
- قيم `service`: `guard | restaurant | kitchen | cleaning | toilet` (strings).

### A.3 خوارزمية الجدولة (كما هي — لن تُستبدل)

`generate_week(conn, start_date_str, toilet_count=3, guard_count=0)`:
1. ينشئ صفًا في `weeks` (start..start+6).
2. الخدمات اليومية الأربع: `guard` → `restaurant` (≠guard) → `kitchen` (≠guard,restaurant) → `cleaning` (≠guard، ويُفضّل ≠restaurant/kitchen).
3. الاختيار عبر `_choose(candidates, usage)`: أقل استخدام، كسر التعادل بترتيب القائمة.
4. **toilet:** فوج واحد للأسبوع كله (الأقل استخداماً إجمالاً) + count يومي لكل الأيام السبعة.

### A.4 التقارير السبعة

1. قائمة الحراسة (أسبوعية)
2. قائمة خدمة المطعم
3. قائمة خدمة المطبخ
4. قائمة خدمة التنظيف
5. قائمة تنظيف المرحاض
6. الخدمات الاختيارية (مع قائد الفوج)
7. قوائم الطلاب

الوظائف العامة المعروضة في UI: توليد PDF للخدمة المحددة → فتح أو طباعة مباشرة (`os.startfile[("print" diag)]` حسب الخيار). المخرجات إلى `%APPDATA%\NationalService\reports`.

### A.5 شاشات Tkinter الحالية وعملياتها

| الشاشة | العمليات |
|---|---|
| Dashboard | إحصائيات، زر إنشاء الأفواج الافتراضية (A1..A5,B1..B5)، طباعة الطلاب |
| Squads/Students | TreeView أفواج+طلاب، فلترة باللفة/الفوج، إضافة/تعديل/حذف فوج وطالب (حوار متعدد الحقول)، طباعة |
| Optional | نموذج إضافة (اسم، عدد، مستلم، فوج، تاريخ، أسبوع)، جدول، حذف، طباعة |
| Weekly | اختيار تاريخ البداية + عدد المرحاض/الحراسة → توليد؛ قائمة الأسابيع؛ تحميل أسبوع؛ **تعديل تعيين يدوي** (حوار: فوج/count/ملاحظات)؛ حذف أسبوع؛ PDF؛ طباعة مباشرة؛ طباعة الاختيارية |
| Settings | `unit_name`، عدد المرحاض، عدد الحراسة، عرض مسار DB |

---

## B. استراتيجية الحفاظ على قاعدة البيانات والترحيل

**لا يوجد أي تغيير في SCHEMA.** SQLite يبقى المصدر الوحيد للحقيقة.

1. **نفس الملف:** الواجهة الجديدة تقرأ/تكتب في نفس `data/service_national.db` عبر نفس `NS_DB_PATH`.
2. **طبقة جديدة بلا نسخ:** FastAPI يستدعي دوال `db.py` و `scheduler.py` كما هي (استيراد مباشر وتمرير `conn`).
3. **نسخة احتياطية قبل أول تشغيل للواجهة الجديدة:** نسخ تلقائي لـ `service_national.db` إلى `data/backup_YYYYMMDD_HHMMSS.db` قبل أي dispatch أول مرة.
4. **بيانات الطلاب الحالية:** لا migration script يُنفَّذ؛ `init_db()` الحالي idempotent (IF NOT EXISTS + ALTERات مُغلفة).
5. في حال رغبة المستخدم لاحقاً بتغيير SCHEMA → منفصل بموافقة صريحة.

---

## C. كيفية تواصل React مع Python (الجسر المحلي)

### الاختيار: **FastAPI على localhost** + WebView/Chromium المحلي

- FastAPI يُشغَّل عبر Uvicorn على `127.0.0.1:8765` (منفذ ثابت مع اختيار آخر تلقائي عند التعارض).
- React (dev: Vite dev server؛ prod: ملفات ثابتة تقدَّم من FastAPI على `/`).
- الواجهة تنادٍ `http://127.0.0.1:8765/api/...` — **لا إنترنت مطلقاً**؛ أصل الاتصال محصور بـ localhost.
- JSON فقط؛ PDF يُفتح عبر endpoint يستدعي `os.startfile` في Python، أو يُرسل كـ base64.

### طبقة الـ API (REST مقترح)

| Area | Endpoints |
|---|---|
| Meta | `GET /api/health`, `GET /api/settings`, `PUT /api/settings` |
| Squads | `GET /api/groups`, `GET /api/squads`, `POST /api/squads`, `PATCH /api/squads/{id}`, `DELETE /api/squads/{id}`, `POST /api/squads/defaults` |
| Students | `GET /api/students?squad_id=&search=`, `POST /api/students`, `PATCH /api/students/{id}`, `DELETE /api/students/{id}` |
| Weeks | `GET /api/weeks`, `POST /api/weeks/generate {start_date, toilet_count, guard_count}`, `DELETE /api/weeks/{id}` |
| Assignments | `GET /api/weeks/{id}/assignments`, `PATCH /api/assignments/{id}`, `PUT /api/assignments/{week}/{day}/{service}` (upsert) |
| Optional | `GET /api/optional?week_id=`, `POST /api/optional`, `PATCH /api/optional/{id}`, `DELETE /api/optional/{id}` |
| Reports | `POST /api/reports/weekly {week_id, service, mode: open\|print}` , `POST /api/reports/students`, `POST /api/reports/optional {week_id}` |
| Dashboard | `GET /api/dashboard` (عدد الطلاب، الأفواج، الأسابيع، آخر أسبوع) |

### ملف جديد: `server.py`
- يستورد `db`, `scheduler`, `reports` بدون أي تعديل عليهم (إلا إضافة `ReportResponse`).
- Pydantic schemas للتحقق.
- CORS محصور على `http://localhost:5173` في وضع dev.
- **Wrong-origin guard:** رفض أي Host ≠ 127.0.0.1/localhost.

### مجلد جديد: `api/`
- `api/routes_meta.py`, `routes_squads.py`, `routes_students.py`, `routes_weeks.py`, `routes_optional.py`, `routes_reports.py`, `schemas.py`

---

## D. معمارية التغليف لسطح المكتب دون إنترنت

الخيارات المُقيّمة:

| الخيار | التوافق مع Python/FastAPI | الحكم |
|---|---|---|
| **Tauri v2 + sidecar Python** | خفيف (~10MB)، لكن يضطر bundling Python runtime — تعقيد Windows | خيار ممكن |
| **PyWebView** | يناسب تماماً: Python `webview.create_window("app", url)` + FastAPI thread؛ حجم صغير؛ بلا فاصّ browsers | ✔ **الموصى به** |
| **PyInstaller onedir + React static** | يعمل مع PyWebView، exe واحد للمجلد | ✔ مع PyWebView |
| **Electron** | كبيرة الحجم، سبق Flask+Node double-process | ✘ غير مفضّل |
| **Flask/Dash** | أقل مرونة من FastAPI+React SPA | ✘ |

**القرار المتوقع:** `server.py` يقدّم:
1. FastAPI (JSON API) على 127.0.0.1.
2. ملفات React `dist/` المبنية كـ static.
3. `pywebview` نافذة كلاسيك تفتح `http://127.0.0.1:8765` بعنوان عربي RTL.
4. إن لم يتوفر webview (تجريب dev): فتح الأفضلية للمتصفح المحلي.

**التقييم الآخر مؤجّل** حتى تأكيد حزم Python 3.12 + ReportLab + arabic-reshaper + pywebview مع PyInstaller (Wyre) — نقطة قرار مع المستخدم قبل المرحلة 5.

---

## E. مواصفات الشاشات (UI.screenSpecs)

> عامة: حجم أساس 14–16px، خط IBM Plex Sans Arabic، `dir="rtl"` على `<html>`، لوحة الشاشة العملية انظر F.

### E.1 لوحة التحكم (Dashboard)
- **أعلى:** شريط علوي — شعار/اسم الوحدة (من settings)، التاريخ بالعربية، حالة DB (local فقط).
- **شبكة 4 بطاقات أوبراشينال:** عدد الطلاب، عدد الأفواج (10)، عدد الأسابيع المولّدة، آخر أسبوع مولّد (تاريخ).
- **عمود عمليات سريعة:** توليد أسبوع جديد (نافذة سريعة)، طباعة قائمة الطلاب، الذهاب للجدول الأسبوعي الحالي.
- **Recharts:** توزيع الخدمات لآخر أسبوع (bar)؛ أعداد الطلاب لكل فوج (horizontal bar).
- **لا أرقام زخرفية:** كل بطاقة أنقر أو مرتبطة بالعمليات.

### E.2 الأفواج والمجموعات
- عمودان: شجرة المجموعات (A/B) + الأفواج (A1..A5/B1..B5) مع `size`.
- أزرار: إضافة فوج، تعديل (الاسم/الرقم/size)، حذف (حوار تأكيد); زر "إنشاء الأفواج الافتراضية" (استدعاء نفس الدالة).
- عدّاد الطلاب لكل فوج داخل البطاقة.

### E.3 إدارة الطلاب
- جدول رئيسي: full_name, rank, squad, national_id, blood_type, phone (RTL، أعمدة متسقة).
- **فلترة:** بحث نصي (full_name / national_id) + تحديد فوج.
- **نافذة الطالب:** 11 حقل (كل الحقول الحالية) — مع Scroll داخل النافذة (نقطة معلّقة من الجلسة السابقة).
- حذف مع تأكيد؛ طباعة PDF الطلاب.
- Pagination بسيطة (مثلاً 50/صفحة).

### E.4 الخدمات الاختيارية
- نموذج إضافة inline (اسم، عدد، مستلم، فوج، تاريخ/أسبوع، ملاحظات).
- جدول ملخص، فحص بفltr الأسبوع، طباعة PDF.

### E.5 الجدول الأسبوعي (الشاشة الأساس — أكبر مساحة عمل)
- **Top bar:** اختيار الأسبوع (dropdown / التقويم) + زر "توليد أسبوع جديد" (modal: start_date, toilet_count default 3, guard_count default 4).
- **الشبكة المركزية:**
  - الصفوف = 7 أيام عربية (السبت..الجمعة) بالتاريخ الهجري؟ لا — ميلادي بتنسيق `YYYY-MM-DD` كما في DB.
  - الأعمدة/الخلايا = الخدمات الخمس: حراسة، مطعم، مطبخ، تنظيف، مرحاض( الأسبوع).
  - كل خلية: اسم الفوج + count بشارة (badge) + ملاحظة (dot).
- **مرحاض:** badge "خدمة الأسبوع" توحّد 7 خلايا بفوج واحد — تظهر منطقاً "week duty".
- **Edit:** نقر خلية → popover تعديل فوج/count/ملاحظات (نفس منطق `edit_assignment`).
- footer أزرار: PDF للخدمة المختارة (قائمة منسدلة بـ7 تقارير)، طباعة مباشرة، طباعة الاختيارية، حذف الأسبوع (تأكيد).

### E.6 محرر الجدول
- بديل تفصيلي للشبكة: table أفقير (assignment rows) مع تحرير مباشر في الخلايا + حفظ كل تعديل عبر `PATCH` — خيار "معاينة متقدمة".

### E.7 التقارير والطباعة
- صفحة dedicates: اختيار الأسبوع + الخدمة (5 أسبوعية + اختيارية + طلاب = 7) + زر معاينة يفتح PDF الحقيقي (فتح الملف من Track)، وسجل آخر PDFs مُنتجة.

### E.8 الإعدادات
- `unit_name` (يظهر في كل رؤوس PDFs)، toilet_daily_count، guard_daily_count، week_start (ثابت Saturday نمایشًا)، مسار DB (read-only)، زر نسخة احتياطية DB (تنفيذ مرحلة 2).

---

## F. نظام التصميم (Design System)

### F.1 الألوان (بدون تدرجات زائدة)

| Token | قيمة | الاستخدام |
|---|---|---|
| `--olive-primary` | `#26382B` | خلفيات الـ Header/Sidebar |
| `--forest` | `#183B2B` | Navbar، الحالات النشطة |
| `--olive` | `#556B2F` | primary buttons، الشارات |
| `--khaki` | `#C2B280` | الأشرطة الثانوية، tags، بطاقات رؤوس |
| `--ivory` | `#F5F3EA` | خلفية الصفحة |
| `--green-DZ` | `#006633` | لون الوحدة الوطنية: حالات إجابية |
| `--red-DZ` | `#D21034` | تحذيرات/حذف فقط — شريط رقيق اختياري في الهوية |
| `--text-dark` | `#202820` | نص أساسي |

### F.2 الطباعة

- **IBM Plex Sans Arabic** (Regular 400 / Medium 500 / Bold 700) — أرقام لاتينية (1,2,3) للاتساق مع DB.
- Scale: page-title 20–22px / section 16px / body 14px / small 12px / badge 11–12px.
- `line-height: 1.6` للأجسام العربية.

### F.3 Spacing & Shape

- Grid 8pt: 4,8,12,16,24,32,48.
- Radius: بطاقات 12px، أزرار 8px، داخلية 6px.
- الظلال خفيفة فقط (`0 1px 3px rgba(32,40,32,.08)`).

### F.4 المكونات (Base components)

`Button` (primary olive / secondary khaki-outline / danger red-DZ / ghost) · `Card` · `Table` (RTL، رأس `#f7f4ea`، صف hover) · `Badge` (squad badge: خلفية olive 10% + text olive؛ count badge: khaki) · `Field` (label above, RTL caret) · `Modal` · `Dropdown/Select` · `DayCell` (الجدول الأسبوعي) · `SidebarItem` · `Toast` · `ConfirmDialog`.

### F.5 التخطيط العام

```
┌────────────────────────────────────────────┐
│ Top bar: اسم الوحدة | التاريخ | حالة DB  │  ← olive-primary
├──────────┬─────────────────────────────────┤
│ Sidebar  │  Content (ivory bg)             │
│ (forest) │                                 │
│ RTL:     │                                 │
│ يمين→يسار│                                 │
└──────────┴─────────────────────────────────┘
```

- Sidebar RTL على اليمين: لوحة التحكم، الأفواج والمجموعات، الطلاب، الخدمات الاختيارية، الجدول الأسبوعي، التقارير، الإعدادات.
- أيقونات: Lucide (hom**, users, calendar-days, file-text, printer, star, settings).

---

## G. خطة التنفيذ المرحلة + الملفات الدقيقة

### المرحلة 2 — الـ API (Python جانب)
- إنشاء `api/__init__.py`, `api/schemas.py`
- `api/routes_meta.py`, `routes_squads.py`, `routes_students.py`, `routes_weeks.py`, `routes_optional.py`, `routes_reports.py`
- `server.py` (FastAPI bootstrap + mount static + PyWebView launch promoted later)
- **تعديل唯一的:** nothing on db.py / scheduler.py / reports.py (استيراد فقط)

### المرحلة 3 — مشروع React skeleton
- `frontend/` (Vite + TS + Tailwind v4)
- `frontend/tailwind.config`, `src/theme/tokens.css`, `src/theme/fonts.css`
- `src/main.tsx`, `src/App.tsx`, `src/api/client.ts` (fetch wrapper + retry + errors)
- `src/components/ui/{Button,Card,Table,Badge,Modal,Toast,ConfirmDialog,Field,Select}.tsx`
- `src/layouts/AppLayout.tsx`

### المرحلة 4 — الشاشات
- `src/pages/Dashboard.tsx`
- `src/pages/Squads.tsx`, `src/pages/Students.tsx`
- `src/pages/OptionalServices.tsx`
- `src/pages/WeeklySchedule.tsx` (الأهم: DayGrid, AssignmentCell, GenerateWeekModal, EditAssignmentPopover)
- `src/pages/ScheduleEditor.tsx`
- `src/pages/Reports.tsx`
- `src/pages/Settings.tsx`
- `src/router.tsx` (React Router)

### المرحلة 5 — التغليف
- `launcher.py` (pywebview wrapper)
- `run_react.bat`ملف جديد ودليل.
- مكّن ملف README/تحديث ملخص.

---

## H. المخاطر ومسائل التوافق

1. **Python runtime حزم من Odoo:** قد لا يمتلك pip ميسّر alert؛ إن احتجنا pip منفصل → نقطة قرار.
2. **PyInstaller + pywebview + reportlab + reshaper:** تجب تجحtrial first build مع الملفات الغيبرادية (Fonts تُقرأ من `C:/Windows/Fonts` — يعمل لأن بيئة Windows).
3. **المنفذ:** phải يتحقق matchmaking المنفذ 8765 مُتاح؛ else اختيار آخر، وReact يحتاج معرفة العنوان — سيُحقن عبر `window.__NS_API__` من webview، أو ملف `port.txt` في `%APPDATA%`.
4. **Squads delete CASCADE:** حذف فوج يمنح set-null للطلاب، وهذا سلوك حالي يجب الإبقاء عليه ممع تنبيه المستخدم.
5. **UNIQUE(week_id, day_index, service):** الـ editor الجديد يجب أن يحترمها عند التعديل (الـ upsert الحالي يعالجها).
6. **day_index mapping:** نص أيام DB بالعربية مصفوفة تبدأ الاثنين لكن الجدول يبدأ السبت حسب اختيار المستخدم — توثيق دقيق في UI لتفادي خلط الاسم/الرقم.
7. **`os.startfile` للطباعة المباشرة:** خارج نطاق webview، يجب أن يبقى في Python side (API endpoint).
8. **لا يصبح هناك أي بدء تلقائي للإنترنت:** حظر fetch خارج localhost عبر ESLint guard في dev + نص الرمز فقط.
9. **حجم الترحيل:** نحتفظ بـ `main.py` و Tkinter كـ fallback كامل — لن تُمس.
10. **قرار packaging مؤجّل** (Tauri vs pywebview) — تم تقييمه، الموصى به: pywebview، القرار النهائي بعد نجاح أول build تجريبي.

---

## I. قائمة اختبارات التحقق بعد الترحيل (must-pass)

1. `main.py` القديم يعمل كما هو، DB نفسها قابلة للفتح من كلى الواجهتين.
2. توليد أسبوع (السبت، toilet=3, guard=4) يطابق سلوك scheduler القديم على نفس DB (نتيجة متطابقة بالـ round-robin).
3. **تعديل يدوي** لتعيين (سquad أو counts) ينصر على کمی DB فعلياً (UNIQUE upsert).
4. إضافة/تعديل/حذف طالب كل الحقول 11.
5. فلترة الطلاب بالابحث + الفوج.
6. إضافة/حذف فوج (شجاً default إنشاء A1..A5,B1..B5 يعمل).
7. إضافة/حذف خدمة اختيارية مع/بدون أسبوع.
8. حذف أسبوع = حذف التعيينات (CASCADE) دون مسس الطلاب.
9. تحميل أسبوع سابق → شبكة السبعة أيام تعممل صحيحاً.
10. إعدادات: تعديل `unit_name` يظهر في رؤوس PDF التالية.
11. **7 تقارير PDF** تُخرج بالعربية الصحيحة وتُفتح/تُطبع مباشرة.
12. بقاء التيار: التطبيق الجديد لا يتصل بأي دوماين غير 127.0.0.1.
13. إنشاء نسخة الاحتياطية الأولى تلقائياً عند أول استخدام للواجهة الجديدة.

---

**الحالة:** المرحلة 1 كاملة — لم يُنفَّذ أي تنفيذ، لم يُعدّل أي ملف حالي بغير إنشاء هذا الملف، لم يُدفع شيء إلى GitHub.
**بانتظار موافقتك لبدء المرحلة 2.**
