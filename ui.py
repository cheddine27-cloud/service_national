import os
import sqlite3
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import db
import scheduler
import reports


AR_FONT = ("Tahoma", 10)


class App(tk.Tk):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.title("نظام الخدمة الوطنية - الجداول والخدمات")
        self.geometry("1200x720")
        self.minsize(1000, 600)
        try:
            self.tk.call("tk", "scaling", 1.2)
        except Exception:
            pass

        # sidebar (right side for RTL feel)
        self.sidebar = tk.Frame(self, width=210, bg="#1f2937")
        self.sidebar.pack(side="right", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self, bg="#f3f4f6")
        self.content.pack(side="left", fill="both", expand=True)

        self.frames = {}
        self._build_sidebar()
        self._build_frames()
        self.show_frame("dashboard")

    def _build_sidebar(self):
        tk.Label(self.sidebar, text="الخدمة الوطنية", fg="white", bg="#1f2937",
                 font=("Tahoma", 13, "bold")).pack(pady=(20, 10))
        items = [
            ("dashboard", "لوحة التحكم"),
            ("squads", "الأفواج والطلاب"),
            ("optional", "الخدمات الاختيارية"),
            ("weekly", "الجداول الأسبوعية"),
            ("settings", "الإعدادات"),
        ]
        for key, label in items:
            b = tk.Button(self.sidebar, text=label, bg="#374151", fg="white",
                          font=AR_FONT, relief="flat", padx=10, pady=8,
                          command=lambda k=key: self.show_frame(k))
            b.pack(fill="x", padx=10, pady=4)

    def _build_frames(self):
        self.frames["dashboard"] = DashboardFrame(self.content, self)
        self.frames["squads"] = SquadsFrame(self.content, self)
        self.frames["optional"] = OptionalFrame(self.content, self)
        self.frames["weekly"] = WeeklyFrame(self.content, self)
        self.frames["settings"] = SettingsFrame(self.content, self)
        for f in self.frames.values():
            f.place(relx=0, rely=0, relwidth=1, relheight=1)

    def show_frame(self, name):
        self.frames[name].tkraise()
        if hasattr(self.frames[name], "refresh"):
            self.frames[name].refresh()

    def open_pdf(self, path, direct=False):
        try:
            if direct:
                os.startfile(path, "print")
            else:
                os.startfile(path)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))


# ---------------- Dashboard ----------------
class DashboardFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f3f4f6")
        self.app = app
        tk.Label(self, text="لوحة التحكم", font=("Tahoma", 16, "bold"), bg="#f3f4f6").pack(pady=20)
        self.info = tk.Label(self, text="", font=AR_FONT, bg="#f3f4f6", justify="right")
        self.info.pack(pady=10)
        btns = tk.Frame(self, bg="#f3f4f6")
        btns.pack(pady=20)
        tk.Button(btns, text="إنشاء الأفواج الافتراضية (10)", font=AR_FONT,
                  command=self.ensure_squads).pack(side="right", padx=5)
        tk.Button(btns, text="طباعة قائمة الطلاب", font=AR_FONT,
                  command=self.print_students).pack(side="right", padx=5)

    def refresh(self):
        conn = self.app.conn
        ns = len(db.list_students(conn))
        sq = len(db.list_squads(conn))
        wk = len(db.list_weeks(conn))
        opt = len(db.list_optional(conn))
        txt = (f"عدد الطلاب: {ns}\n"
               f"عدد الأفواج: {sq}\n"
               f"عدد الجداول الأسبوعية: {wk}\n"
               f"عدد الخدمات الاختيارية: {opt}")
        self.info.config(text=txt)

    def ensure_squads(self):
        db.ensure_default_squads(self.app.conn)
        messagebox.showinfo("تم", "تم إنشاء/التأكد من الأفواج (10).")
        self.refresh()

    def print_students(self):
        path = reports.generate_students_pdf(self.app.conn)
        self.app.open_pdf(path)


# ---------------- Squads & Students ----------------
class SquadsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f3f4f6")
        self.app = app
        tk.Label(self, text="الأفواج والطلاب", font=("Tahoma", 16, "bold"), bg="#f3f4f6").pack(pady=10)

        # squads section
        top = tk.Frame(self, bg="#f3f4f6")
        top.pack(fill="x", padx=10)
        tk.Button(top, text="إضافة فوج", font=AR_FONT, command=self.add_squad).pack(side="right", padx=5)
        tk.Button(top, text="إنشاء الأفواج الافتراضية", font=AR_FONT, command=self.ensure_squads).pack(side="right", padx=5)
        tk.Button(top, text="حذف فوج", font=AR_FONT, command=self.delete_squad).pack(side="right", padx=5)

        self.squad_tree = ttk.Treeview(self, columns=("group", "number", "name", "size"), show="headings", height=6)
        for c, t, w in (("group", "المجموعة", 80), ("number", "رقم", 60), ("name", "اسم الفوج", 120), ("size", "العدد", 80)):
            self.squad_tree.heading(c, text=t)
            self.squad_tree.column(c, width=w, anchor="e")
        self.squad_tree.pack(fill="x", padx=10, pady=5)

        # students section
        mid = tk.Frame(self, bg="#f3f4f6")
        mid.pack(fill="x", padx=10, pady=(10, 0))
        tk.Label(mid, text="الطلاب", font=("Tahoma", 12, "bold"), bg="#f3f4f6").pack(side="right")
        self.filter_var = tk.StringVar(value="الكل")
        tk.Label(mid, text="فلتر حسب الفوج:", bg="#f3f4f6", font=AR_FONT).pack(side="right", padx=5)
        self.filter_combo = ttk.Combobox(mid, textvariable=self.filter_var, state="readonly", width=15)
        self.filter_combo.pack(side="right", padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_students())
        tk.Button(mid, text="إضافة طالب", font=AR_FONT, command=self.add_student).pack(side="left", padx=5)
        tk.Button(mid, text="تعديل", font=AR_FONT, command=self.edit_student).pack(side="left", padx=5)
        tk.Button(mid, text="حذف", font=AR_FONT, command=self.delete_student).pack(side="left", padx=5)
        tk.Button(mid, text="طباعة", font=AR_FONT, command=self.print_students).pack(side="left", padx=5)

        self.stu_tree = ttk.Treeview(self, columns=("name", "squad", "nid", "birth", "phone", "notes"), show="headings", height=16)
        for c, t, w in (("name", "الاسم", 160), ("squad", "الفوج", 70), ("nid", "الرقم الوطني", 110),
                        ("birth", "تاريخ الميلاد", 100), ("phone", "الهاتف", 100), ("notes", "ملاحظات", 120)):
            self.stu_tree.heading(c, text=t)
            self.stu_tree.column(c, width=w, anchor="e")
        self.stu_tree.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh(self):
        self.refresh_squads()
        self.refresh_filter()
        self.refresh_students()

    def refresh_squads(self):
        for r in self.squad_tree.get_children():
            self.squad_tree.delete(r)
        for s in db.list_squads(self.app.conn):
            self.squad_tree.insert("", "end", iid=s["id"], values=(s["group_code"], s["number"], s["name"], s["size"]))

    def refresh_filter(self):
        vals = ["الكل"] + [s["name"] for s in db.list_squads(self.app.conn)]
        self.filter_combo["values"] = vals
        if self.filter_var.get() not in vals:
            self.filter_var.set("الكل")

    def refresh_students(self):
        for r in self.stu_tree.get_children():
            self.stu_tree.delete(r)
        fv = self.filter_var.get()
        squad_id = None
        if fv != "الكل":
            for s in db.list_squads(self.app.conn):
                if s["name"] == fv:
                    squad_id = s["id"]
        for st in db.list_students(self.app.conn, squad_id=squad_id):
            self.stu_tree.insert("", "end", iid=st["id"], values=(
                st["full_name"], st.get("squad_name") or "-", st.get("national_id") or "",
                st.get("birth_date") or "", st.get("phone") or "", st.get("notes") or ""))

    def ensure_squads(self):
        db.ensure_default_squads(self.app.conn)
        self.refresh()

    def add_squad(self):
        dlg = tk.Toplevel(self)
        dlg.title("إضافة فوج")
        dlg.geometry("320x220")
        gvar = tk.StringVar(value="A")
        nvar = tk.StringVar(value="1")
        namevar = tk.StringVar()
        sizevar = tk.StringVar(value="0")
        for label, var, widget in (("المجموعة (A/B):", gvar, None),):
            pass
        tk.Label(dlg, text="المجموعة:", font=AR_FONT).pack(anchor="e", padx=10, pady=5)
        ttk.Combobox(dlg, textvariable=gvar, values=["A", "B"], state="readonly").pack(fill="x", padx=10)
        tk.Label(dlg, text="رقم الفوج:", font=AR_FONT).pack(anchor="e", padx=10, pady=5)
        tk.Entry(dlg, textvariable=nvar, font=AR_FONT).pack(fill="x", padx=10)
        tk.Label(dlg, text="اسم الفوج (اختياري):", font=AR_FONT).pack(anchor="e", padx=10, pady=5)
        tk.Entry(dlg, textvariable=namevar, font=AR_FONT).pack(fill="x", padx=10)
        tk.Label(dlg, text="العدد:", font=AR_FONT).pack(anchor="e", padx=10, pady=5)
        tk.Entry(dlg, textvariable=sizevar, font=AR_FONT).pack(fill="x", padx=10)

        def save():
            try:
                num = int(nvar.get())
                size = int(sizevar.get() or 0)
            except ValueError:
                messagebox.showerror("خطأ", "أدخل أرقاماً صحيحة")
                return
            name = namevar.get().strip() or None
            try:
                db.create_squad(self.app.conn, gvar.get(), num, name, size)
            except Exception as e:
                messagebox.showerror("خطأ", str(e))
                return
            dlg.destroy()
            self.refresh()

        tk.Button(dlg, text="حفظ", font=AR_FONT, command=save).pack(pady=10)

    def delete_squad(self):
        sel = self.squad_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر فوجاً")
            return
        sid = int(sel[0])
        if not messagebox.askyesno("تأكيد", "حذف الفوج؟ (سيؤثر على الطلاب)"):
            return
        db.delete_squad(self.app.conn, sid)
        self.refresh()

    def add_student(self):
        self._student_dialog(None)

    def edit_student(self):
        sel = self.stu_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر طالباً")
            return
        self._student_dialog(int(sel[0]))

    def _student_dialog(self, student_id):
        st = None
        if student_id:
            for s in db.list_students(self.app.conn):
                if s["id"] == student_id:
                    st = s
                    break
        dlg = tk.Toplevel(self)
        dlg.title("بيانات طالب")
        dlg.geometry("420x620")
        vars = {
            "full_name": tk.StringVar(value=st["full_name"] if st else ""),
            "father_name": tk.StringVar(value=st.get("father_name", "") if st else ""),
            "national_id": tk.StringVar(value=st.get("national_id", "") if st else ""),
            "birth_date": tk.StringVar(value=st.get("birth_date", "") if st else ""),
            "phone": tk.StringVar(value=st.get("phone", "") if st else ""),
            "address": tk.StringVar(value=st.get("address", "") if st else ""),
            "blood_type": tk.StringVar(value=st.get("blood_type", "") if st else ""),
            "rank": tk.StringVar(value=st.get("rank", "") if st else ""),
            "enlistment_date": tk.StringVar(value=st.get("enlistment_date", "") if st else ""),
            "notes": tk.StringVar(value=st.get("notes", "") if st else ""),
        }
        squad_var = tk.StringVar()
        squads = db.list_squads(self.app.conn)
        squad_names = [s["name"] for s in squads]
        if st and st.get("squad_name"):
            squad_var.set(st["squad_name"])
        elif squads:
            squad_var.set(squads[0]["name"])

        fields = [("الاسم (كامل):", "full_name"), ("اسم الأب:", "father_name"),
                  ("الرقم الوطني:", "national_id"), ("تاريخ الميلاد (YYYY-MM-DD):", "birth_date"),
                  ("الهاتف:", "phone"), ("العنوان:", "address"), ("فصيلة الدم:", "blood_type"),
                  ("الرتبة/الصف:", "rank"), ("تاريخ الالتحاق:", "enlistment_date"), ("ملاحظات:", "notes")]
        for label, key in fields:
            tk.Label(dlg, text=label, font=AR_FONT).pack(anchor="e", padx=10, pady=2)
            tk.Entry(dlg, textvariable=vars[key], font=AR_FONT).pack(fill="x", padx=10)
        tk.Label(dlg, text="الفوج:", font=AR_FONT).pack(anchor="e", padx=10, pady=2)
        ttk.Combobox(dlg, textvariable=squad_var, values=squad_names, state="readonly").pack(fill="x", padx=10)

        def save():
            name = vars["full_name"].get().strip()
            if not name:
                messagebox.showerror("خطأ", "الاسم مطلوب")
                return
            sid = None
            for s in squads:
                if s["name"] == squad_var.get():
                    sid = s["id"]
            data = {k: vars[k].get().strip() for k in vars}
            data["squad_id"] = sid
            data["full_name"] = name
            try:
                if student_id:
                    db.update_student(self.app.conn, student_id, **data)
                else:
                    db.create_student(self.app.conn, **data)
            except Exception as e:
                messagebox.showerror("خطأ", str(e))
                return
            dlg.destroy()
            self.refresh_students()

        tk.Button(dlg, text="حفظ", font=AR_FONT, command=save).pack(pady=10)

    def delete_student(self):
        sel = self.stu_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر طالباً")
            return
        if not messagebox.askyesno("تأكيد", "حذف الطالب؟"):
            return
        db.delete_student(self.app.conn, int(sel[0]))
        self.refresh_students()

    def print_students(self):
        path = reports.generate_students_pdf(self.app.conn)
        self.app.open_pdf(path)


# ---------------- Optional Services ----------------
class OptionalFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f3f4f6")
        self.app = app
        tk.Label(self, text="الخدمات الاختيارية", font=("Tahoma", 16, "bold"), bg="#f3f4f6").pack(pady=10)

        form = tk.Frame(self, bg="#f3f4f6")
        form.pack(fill="x", padx=10)
        self.v_name = tk.StringVar()
        self.v_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.v_count = tk.StringVar(value="1")
        self.v_receiver = tk.StringVar()
        self.v_notes = tk.StringVar()
        self.v_squad = tk.StringVar()
        self.v_week = tk.StringVar(value="بدون")

        def row(label, widget):
            f = tk.Frame(form, bg="#f3f4f6")
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, font=AR_FONT, width=18, anchor="e").pack(side="right")
            widget.pack(side="right", fill="x", expand=True)

        row("اسم الخدمة:", tk.Entry(form, textvariable=self.v_name, font=AR_FONT))
        # fix row packing: above wrong; redo manually
        # We'll just pack entries directly instead:
        form.pack_forget()

        # rebuild clean
        form = tk.Frame(self, bg="#f3f4f6")
        form.pack(fill="x", padx=10)
        grid = tk.Frame(form, bg="#f3f4f6")
        grid.pack(fill="x")

        def addrow(r, label, widget):
            tk.Label(grid, text=label, font=AR_FONT, anchor="e").grid(row=r, column=1, sticky="e", padx=5, pady=3)
            widget.grid(row=r, column=0, sticky="ew", padx=5, pady=3)

        grid.columnconfigure(0, weight=1)
        addrow(0, "اسم الخدمة:", tk.Entry(grid, textvariable=self.v_name, font=AR_FONT))
        addrow(1, "التاريخ:", tk.Entry(grid, textvariable=self.v_date, font=AR_FONT))
        addrow(2, "العدد:", tk.Entry(grid, textvariable=self.v_count, font=AR_FONT))
        addrow(3, "اسم المستلم:", tk.Entry(grid, textvariable=self.v_receiver, font=AR_FONT))
        squads = db.list_squads(self.app.conn)
        self.v_squad.set(squads[0]["name"] if squads else "")
        addrow(4, "الفوج (المستلم):", ttk.Combobox(grid, textvariable=self.v_squad, values=[s["name"] for s in squads], state="readonly"))
        weeks = db.list_weeks(self.app.conn)
        week_vals = ["بدون"] + [f"{w['id']} ({w['start_date']})" for w in weeks]
        self.v_week.set("بدون")
        self.week_combo = ttk.Combobox(grid, textvariable=self.v_week, values=week_vals, state="readonly")
        addrow(5, "الأسبوع (اختياري):", self.week_combo)
        addrow(6, "ملاحظات:", tk.Entry(grid, textvariable=self.v_notes, font=AR_FONT))

        bf = tk.Frame(self, bg="#f3f4f6")
        bf.pack(fill="x", padx=10, pady=5)
        tk.Button(bf, text="إضافة", font=AR_FONT, command=self.add_optional).pack(side="right", padx=5)
        tk.Button(bf, text="حذف", font=AR_FONT, command=self.delete_optional).pack(side="right", padx=5)
        tk.Button(bf, text="طباعة قائمة الاختيارية", font=AR_FONT, command=self.print_optional).pack(side="right", padx=5)

        self.tree = ttk.Treeview(self, columns=("name", "date", "count", "receiver", "squad", "notes"), show="headings", height=16)
        for c, t, w in (("name", "اسم الخدمة", 130), ("date", "التاريخ", 100), ("count", "العدد", 60),
                        ("receiver", "المستلم", 120), ("squad", "الفوج", 70), ("notes", "ملاحظات", 150)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for o in db.list_optional(self.app.conn):
            self.tree.insert("", "end", iid=o["id"], values=(
                o["name"], o.get("date") or "", o.get("count") or 0, o.get("receiver") or "",
                o.get("squad_name") or "-", o.get("notes") or ""))
        weeks = db.list_weeks(self.app.conn)
        self.week_combo["values"] = ["بدون"] + [f"{w['id']} ({w['start_date']})" for w in weeks]

    def add_optional(self):
        name = self.v_name.get().strip()
        if not name:
            messagebox.showerror("خطأ", "اسم الخدمة مطلوب")
            return
        try:
            count = int(self.v_count.get() or 0)
        except ValueError:
            messagebox.showerror("خطأ", "العدد يجب أن يكون رقماً")
            return
        squad_id = None
        for s in db.list_squads(self.app.conn):
            if s["name"] == self.v_squad.get():
                squad_id = s["id"]
        week_id = None
        wv = self.v_week.get()
        if wv != "بدون":
            try:
                week_id = int(wv.split()[0])
            except Exception:
                week_id = None
        try:
            db.create_optional(self.app.conn, week_id=week_id, date=self.v_date.get().strip() or None,
                               name=name, count=count, receiver=self.v_receiver.get().strip() or None,
                               squad_id=squad_id, notes=self.v_notes.get().strip() or None)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))
            return
        messagebox.showinfo("تم", "تمت الإضافة")
        self.v_name.set("")
        self.v_notes.set("")
        self.refresh()

    def delete_optional(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر خدمة")
            return
        if not messagebox.askyesno("تأكيد", "حذف الخدمة؟"):
            return
        db.delete_optional(self.app.conn, int(sel[0]))
        self.refresh()

    def print_optional(self):
        week_id = None
        wv = self.v_week.get()
        if wv != "بدون":
            try:
                week_id = int(wv.split()[0])
            except Exception:
                week_id = None
        path = reports.generate_optional_pdf(self.app.conn, week_id)
        self.app.open_pdf(path)


# ---------------- Weekly Schedule ----------------
class WeeklyFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f3f4f6")
        self.app = app
        tk.Label(self, text="الجداول الأسبوعية", font=("Tahoma", 16, "bold"), bg="#f3f4f6").pack(pady=10)

        top = tk.Frame(self, bg="#f3f4f6")
        top.pack(fill="x", padx=10)
        tk.Label(top, text="تاريخ بداية الأسبوع (YYYY-MM-DD):", font=AR_FONT).pack(side="right", padx=5)
        # default to upcoming Saturday
        today = datetime.now().date()
        days_until_sat = (5 - today.weekday()) % 7
        if days_until_sat == 0:
            days_until_sat = 0
        default_start = today + timedelta(days=days_until_sat)
        self.start_var = tk.StringVar(value=default_start.strftime("%Y-%m-%d"))
        tk.Entry(top, textvariable=self.start_var, font=AR_FONT, width=14).pack(side="right", padx=5)
        tk.Button(top, text="توليد جدول", font=AR_FONT, command=self.generate).pack(side="right", padx=5)

        tk.Label(top, text="الأسبوع:", font=AR_FONT).pack(side="left", padx=5)
        self.week_var = tk.StringVar()
        self.week_combo = ttk.Combobox(top, textvariable=self.week_var, state="readonly", width=28)
        self.week_combo.pack(side="left", padx=5)
        self.week_combo.bind("<<ComboboxSelected>>", lambda e: self.load_week())
        tk.Button(top, text="حذف أسبوع", font=AR_FONT, command=self.delete_week).pack(side="left", padx=5)

        # main table
        self.tree = ttk.Treeview(self, columns=("day", "date", "guard", "restaurant", "kitchen", "cleaning", "toilet"), show="headings", height=9)
        headers = [("day", "اليوم", 90), ("date", "التاريخ", 100), ("guard", "الحراسة", 110),
                   ("restaurant", "المطعم", 110), ("kitchen", "المطبخ", 110),
                   ("cleaning", "التنظيف", 110), ("toilet", "المرحاض (فوج/عدد)", 150)]
        for c, t, w in headers:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="e")
        self.tree.pack(fill="x", padx=10, pady=8)

        # edit + print buttons
        bf = tk.Frame(self, bg="#f3f4f6")
        bf.pack(fill="x", padx=10, pady=5)
        tk.Button(bf, text="تعديل تعيين", font=AR_FONT, command=self.edit_assignment).pack(side="right", padx=5)
        tk.Label(bf, text="نوع القائمة:", font=AR_FONT).pack(side="right", padx=5)
        self.print_type = tk.StringVar(value="restaurant")
        ttk.Combobox(bf, textvariable=self.print_type, state="readonly", width=14,
                     values=["guard", "restaurant", "kitchen", "cleaning", "toilet"]).pack(side="right", padx=5)
        tk.Button(bf, text="توليد PDF", font=AR_FONT, command=self.make_pdf).pack(side="right", padx=5)
        tk.Button(bf, text="طباعة مباشرة", font=AR_FONT, command=self.print_direct).pack(side="right", padx=5)
        tk.Button(bf, text="طباعة الاختيارية", font=AR_FONT, command=self.print_optional).pack(side="right", padx=5)

        self.status = tk.Label(self, text="", font=AR_FONT, bg="#f3f4f6", fg="#374151")
        self.status.pack(pady=5)

    def refresh(self):
        self.refresh_weeks()

    def refresh_weeks(self):
        weeks = db.list_weeks(self.app.conn)
        vals = [f"{w['id']} ({w['start_date']} → {w['end_date']})" for w in weeks]
        self.week_combo["values"] = vals
        if vals and not self.week_var.get():
            self.week_var.set(vals[0])
        self.load_week()

    def current_week_id(self):
        wv = self.week_var.get()
        if not wv:
            return None
        try:
            return int(wv.split()[0])
        except Exception:
            return None

    def generate(self):
        try:
            sd = self.start_var.get().strip()
            datetime.strptime(sd, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("خطأ", "صيغة التاريخ YYYY-MM-DD")
            return
        toilet_count = 3
        guard_count = 0
        try:
            toilet_count = int(db.get_setting(self.app.conn, "toilet_daily_count", "3"))
        except Exception:
            pass
        try:
            guard_count = int(db.get_setting(self.app.conn, "guard_daily_count", "0"))
        except Exception:
            pass
        try:
            wid = scheduler.generate_week(self.app.conn, sd, toilet_count, guard_count)
        except Exception as e:
            messagebox.showerror("خطأ", str(e))
            return
        messagebox.showinfo("تم", f"تم توليد الأسبوع #{wid}")
        self.refresh_weeks()
        self.week_var.set(f"{wid} ({sd} → ...)")
        self.load_week()

    def load_week(self):
        wid = self.current_week_id()
        for r in self.tree.get_children():
            self.tree.delete(r)
        if wid is None:
            return
        assigns = db.get_assignments(self.app.conn, wid)
        # index
        by_day_service = {}
        for a in assigns:
            by_day_service.setdefault(a["day_index"], {}).setdefault(a["service"], a)
        week = db.get_week(self.app.conn, wid)
        start = datetime.strptime(week["start_date"], "%Y-%m-%d").date()
        for d in range(7):
            day_date = (start + timedelta(days=d)).isoformat()
            day_name = db.DAY_NAMES_AR.get(datetime.strptime(day_date, "%Y-%m-%d").weekday(), "")
            dd = by_day_service.get(d, {})
            guard = dd.get("guard", {}).get("squad_name", "-") if dd.get("guard") else "-"
            rest = dd.get("restaurant", {}).get("squad_name", "-") if dd.get("restaurant") else "-"
            kit = dd.get("kitchen", {}).get("squad_name", "-") if dd.get("kitchen") else "-"
            clean = dd.get("cleaning", {}).get("squad_name", "-") if dd.get("cleaning") else "-"
            t = dd.get("toilet", {})
            toilet_txt = f"{t.get('squad_name','-')} ({t.get('count',0)})" if t else "-"
            self.tree.insert("", "end", iid=str(d), values=(day_name, day_date, guard, rest, kit, clean, toilet_txt))
        self.status.config(text=f"الأسبوع #{wid}: {week['start_date']} → {week['end_date']}")

    def delete_week(self):
        wid = self.current_week_id()
        if wid is None:
            return
        if not messagebox.askyesno("تأكيد", "حذف الأسبوع وجميع تعييناته؟"):
            return
        db.delete_week(self.app.conn, wid)
        self.week_var.set("")
        self.refresh_weeks()

    def edit_assignment(self):
        wid = self.current_week_id()
        if wid is None:
            messagebox.showwarning("تنبيه", "اختر أسبوعاً")
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "اختر يوماً")
            return
        day_index = int(sel[0])
        # choose service
        svc = self.print_type.get() or "restaurant"
        dlg = tk.Toplevel(self)
        dlg.title("تعديل تعيين")
        dlg.geometry("360x260")
        squads = db.list_squads(self.app.conn)
        sq_names = [s["name"] for s in squads]
        squad_var = tk.StringVar()
        count_var = tk.StringVar(value="0")
        notes_var = tk.StringVar()
        # load current
        assigns = db.get_assignments(self.app.conn, wid)
        cur = None
        for a in assigns:
            if a["day_index"] == day_index and a["service"] == svc:
                cur = a
                break
        if cur:
            if cur.get("squad_name"):
                squad_var.set(cur["squad_name"])
            count_var.set(str(cur.get("count") or 0))
            notes_var.set(cur.get("notes") or "")

        tk.Label(dlg, text=f"اليوم index: {day_index}  الخدمة: {svc}", font=AR_FONT).pack(pady=5)
        tk.Label(dlg, text="الفوج:", font=AR_FONT).pack(anchor="e", padx=10)
        ttk.Combobox(dlg, textvariable=squad_var, values=sq_names, state="readonly").pack(fill="x", padx=10)
        tk.Label(dlg, text="العدد:", font=AR_FONT).pack(anchor="e", padx=10)
        tk.Entry(dlg, textvariable=count_var, font=AR_FONT).pack(fill="x", padx=10)
        tk.Label(dlg, text="ملاحظات:", font=AR_FONT).pack(anchor="e", padx=10)
        tk.Entry(dlg, textvariable=notes_var, font=AR_FONT).pack(fill="x", padx=10)

        def save():
            squad_id = None
            for s in squads:
                if s["name"] == squad_var.get():
                    squad_id = s["id"]
            try:
                count = int(count_var.get() or 0)
            except ValueError:
                messagebox.showerror("خطأ", "العدد يجب أن يكون رقماً")
                return
            week = db.get_week(self.app.conn, wid)
            start = datetime.strptime(week["start_date"], "%Y-%m-%d").date()
            day_date = (start + timedelta(days=day_index)).isoformat()
            db.upsert_assignment(self.app.conn, wid, day_index, day_date, svc, squad_id, count, notes_var.get().strip() or None)
            dlg.destroy()
            self.load_week()

        tk.Button(dlg, text="حفظ", font=AR_FONT, command=save).pack(pady=10)

    def make_pdf(self):
        wid = self.current_week_id()
        if wid is None:
            messagebox.showwarning("تنبيه", "اختر أسبوعاً")
            return
        svc = self.print_type.get()
        path = reports.generate_weekly_pdf(self.app.conn, wid, svc)
        self.app.open_pdf(path)

    def print_direct(self):
        wid = self.current_week_id()
        if wid is None:
            messagebox.showwarning("تنبيه", "اختر أسبوعاً")
            return
        svc = self.print_type.get()
        path = reports.generate_weekly_pdf(self.app.conn, wid, svc)
        self.app.open_pdf(path, direct=True)

    def print_optional(self):
        wid = self.current_week_id()
        path = reports.generate_optional_pdf(self.app.conn, wid)
        self.app.open_pdf(path)


# ---------------- Settings ----------------
class SettingsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f3f4f6")
        self.app = app
        tk.Label(self, text="الإعدادات", font=("Tahoma", 16, "bold"), bg="#f3f4f6").pack(pady=10)
        self.unit_var = tk.StringVar()
        self.toilet_var = tk.StringVar()
        self.guard_var = tk.StringVar()
        form = tk.Frame(self, bg="#f3f4f6")
        form.pack(fill="x", padx=20)
        tk.Label(form, text="اسم الوحدة/الخدمة:", font=AR_FONT).pack(anchor="e", pady=5)
        tk.Entry(form, textvariable=self.unit_var, font=AR_FONT).pack(fill="x")
        tk.Label(form, text="العدد الافتراضي يومياً للمرحاض:", font=AR_FONT).pack(anchor="e", pady=5)
        tk.Entry(form, textvariable=self.toilet_var, font=AR_FONT).pack(fill="x")
        tk.Label(form, text="العدد الافتراضي يومياً للحراسة:", font=AR_FONT).pack(anchor="e", pady=5)
        tk.Entry(form, textvariable=self.guard_var, font=AR_FONT).pack(fill="x")
        tk.Label(form, text=f"مسار قاعدة البيانات: {db.get_db_path()}", font=AR_FONT, fg="#6b7280").pack(anchor="e", pady=10)
        tk.Button(form, text="حفظ", font=AR_FONT, command=self.save).pack(pady=10)

    def refresh(self):
        self.unit_var.set(db.get_setting(self.app.conn, "unit_name", "الخدمة الوطنية"))
        self.toilet_var.set(db.get_setting(self.app.conn, "toilet_daily_count", "3"))
        self.guard_var.set(db.get_setting(self.app.conn, "guard_daily_count", "0"))

    def save(self):
        db.set_setting(self.app.conn, "unit_name", self.unit_var.get().strip() or "الخدمة الوطنية")
        try:
            int(self.toilet_var.get())
            int(self.guard_var.get())
        except ValueError:
            messagebox.showerror("خطأ", "العدد يجب أن يكون رقماً")
            return
        db.set_setting(self.app.conn, "toilet_daily_count", self.toilet_var.get().strip())
        db.set_setting(self.app.conn, "guard_daily_count", self.guard_var.get().strip())
        messagebox.showinfo("تم", "تم حفظ الإعدادات")
