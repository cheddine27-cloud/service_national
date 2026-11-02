import os
import arabic_reshaper
from bidi.algorithm import get_display
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import db


def _register_fonts():
    regular = "C:/Windows/Fonts/tahoma.ttf"
    bold = "C:/Windows/Fonts/tahomabd.ttf"
    if not os.path.exists(bold):
        bold = regular
    pdfmetrics.registerFont(TTFont("Arabic", regular))
    pdfmetrics.registerFont(TTFont("ArabicBold", bold))


def ar(text):
    if text is None:
        text = ""
    text = str(text)
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text


def _out_path(prefix):
    d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NationalService", "reports")
    os.makedirs(d, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(d, f"{prefix}_{ts}.pdf")


SERVICE_TITLES = {
    "guard": "قائمة الحراسة (أسبوعية)",
    "restaurant": "قائمة خدمة المطعم (أسبوعية)",
    "kitchen": "قائمة خدمة المطبخ (أسبوعية)",
    "cleaning": "قائمة خدمة التنظيف (أسبوعية)",
    "toilet": "قائمة تنظيف الحمامات/المرحاض (أسبوعية)",
}


def _week_range(week):
    return f"{week['start_date']}  إلى  {week['end_date']}"


def generate_weekly_pdf(conn, week_id, service):
    _register_fonts()
    week = db.get_week(conn, week_id)
    unit = db.get_setting(conn, "unit_name", "الخدمة الوطنية")
    assignments = db.get_assignments(conn, week_id, service)
    # group by day_index
    by_day = {}
    for a in assignments:
        by_day.setdefault(a["day_index"], []).append(a)

    title = SERVICE_TITLES.get(service, "قائمة خدمة")
    path = _out_path(service)

    doc = SimpleDocTemplate(path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleAr", fontName="ArabicBold", fontSize=16,
                                 alignment=2, spaceAfter=6)  # 2 = right? reportlab alignment: 0 left,1 center,2 right? Actually 2 right
    # reportlab alignment constants: TA_LEFT=0, TA_CENTER=1, TA_RIGHT=2
    sub_style = ParagraphStyle("SubAr", fontName="Arabic", fontSize=11, alignment=2, spaceAfter=4)
    normal = ParagraphStyle("NormalAr", fontName="Arabic", fontSize=10, alignment=2)

    story.append(Paragraph(ar(unit), title_style))
    story.append(Paragraph(ar(title), title_style))
    story.append(Paragraph(ar(f"الأسبوع: {_week_range(week)}"), sub_style))
    story.append(Paragraph(ar(f"تاريخ التوليد: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Spacer(1, 0.3*cm))

    # Build table data
    if service in ("toilet", "guard"):
        header = [ar("ملاحظات"), ar("العدد"), ar("الفوج"), ar("التاريخ"), ar("اليوم")]
        rows = [header]
        for d in range(7):
            day_assigns = by_day.get(d, [])
            if day_assigns:
                a = day_assigns[0]
                squad = a.get("squad_name") or "-"
                cnt = a.get("count") or 0
                note = a.get("notes") or ""
                day_date = a["date"]
                day_name = db.DAY_NAMES_AR.get(datetime.strptime(day_date, "%Y-%m-%d").weekday(), "")
                rows.append([ar(note), ar(cnt), ar(squad), ar(day_date), ar(day_name)])
    else:
        header = [ar("ملاحظات"), ar("الفوج"), ar("التاريخ"), ar("اليوم")]
        rows = [header]
        for d in range(7):
            day_assigns = by_day.get(d, [])
            if day_assigns:
                a = day_assigns[0]
                squad = a.get("squad_name") or "-"
                note = a.get("notes") or ""
                day_date = a["date"]
                day_name = db.DAY_NAMES_AR.get(datetime.strptime(day_date, "%Y-%m-%d").weekday(), "")
                rows.append([ar(note), ar(squad), ar(day_date), ar(day_name)])

    col_widths = None
    if service in ("toilet", "guard"):
        col_widths = [4*cm, 2*cm, 3*cm, 3*cm, 3*cm]
    else:
        col_widths = [4*cm, 3*cm, 3*cm, 3*cm]

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Arabic"),
        ("FONTNAME", (0, 0), (-1, 0), "ArabicBold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.6*cm))

    # Signature area
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.3*cm))
    sig_style = ParagraphStyle("Sig", fontName="Arabic", fontSize=10, alignment=2, spaceAfter=2)
    story.append(Paragraph(ar("المسؤول (الضابط): ____________________    التوقيع: ____________________    التاريخ: ____/____/____"), sig_style))
    if service in ("kitchen", "restaurant"):
        story.append(Paragraph(ar("المستلم (قائد الفوج): ____________________    التوقيع: ____________________"), sig_style))
    if service == "toilet":
        story.append(Paragraph(ar("مسؤول النظافة: ____________________    التوقيع: ____________________"), sig_style))
    story.append(Paragraph(ar("قائد الوحدة: ____________________    التوقيع والختم: ____________________"), sig_style))

    doc.build(story)
    return path


def generate_optional_pdf(conn, week_id=None):
    _register_fonts()
    unit = db.get_setting(conn, "unit_name", "الخدمة الوطنية")
    rows_data = db.list_optional(conn, week_id)
    week = db.get_week(conn, week_id) if week_id else None
    path = _out_path("optional")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []
    title_style = ParagraphStyle("TitleAr", fontName="ArabicBold", fontSize=16, alignment=2, spaceAfter=6)
    sub_style = ParagraphStyle("SubAr", fontName="Arabic", fontSize=11, alignment=2, spaceAfter=4)
    sig_style = ParagraphStyle("Sig", fontName="Arabic", fontSize=10, alignment=2, spaceAfter=2)

    story.append(Paragraph(ar(unit), title_style))
    story.append(Paragraph(ar("قائمة الخدمات الاختيارية"), title_style))
    if week:
        story.append(Paragraph(ar(f"الأسبوع: {week['start_date']}  إلى  {week['end_date']}"), sub_style))
    story.append(Paragraph(ar(f"تاريخ التوليد: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), sub_style))
    story.append(Spacer(1, 0.3*cm))

    header = [ar("ملاحظات"), ar("الفوج"), ar("المستلم"), ar("العدد"), ar("اسم الخدمة"), ar("التاريخ")]
    rows = [header]
    for o in rows_data:
        rows.append([
            ar(o.get("notes") or ""),
            ar(o.get("squad_name") or "-"),
            ar(o.get("receiver") or "-"),
            ar(o.get("count") or 0),
            ar(o.get("name") or ""),
            ar(o.get("date") or ""),
        ])
    if len(rows) == 1:
        rows.append([ar("لا توجد بيانات"), "", "", "", "", ""])

    table = Table(rows, colWidths=[3*cm, 2.5*cm, 3*cm, 1.5*cm, 3.5*cm, 2.5*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Arabic"),
        ("FONTNAME", (0, 0), (-1, 0), "ArabicBold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(ar("المسؤول (الضابط): ____________________    التوقيع: ____________________    التاريخ: ____/____/____"), sig_style))
    story.append(Paragraph(ar("المستلم (في المطبخ/المخزن): ____________________    التوقيع: ____________________"), sig_style))
    story.append(Paragraph(ar("قائد الفوج (المستلم): ____________________    التوقيع: ____________________"), sig_style))
    story.append(Paragraph(ar("قائد الوحدة: ____________________    التوقيع والختم: ____________________"), sig_style))

    doc.build(story)
    return path


def generate_students_pdf(conn):
    _register_fonts()
    unit = db.get_setting(conn, "unit_name", "الخدمة الوطنية")
    students = db.list_students(conn)
    path = _out_path("students")

    doc = SimpleDocTemplate(path, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []
    title_style = ParagraphStyle("TitleAr", fontName="ArabicBold", fontSize=16, alignment=2, spaceAfter=6)
    sub_style = ParagraphStyle("SubAr", fontName="Arabic", fontSize=11, alignment=2, spaceAfter=4)

    story.append(Paragraph(ar(unit), title_style))
    story.append(Paragraph(ar("قائمة بيانات الطلاب"), title_style))
    story.append(Paragraph(ar(f"تاريخ التوليد: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), sub_style))
    story.append(Spacer(1, 0.3*cm))

    header = [ar("ملاحظات"), ar("الهاتف"), ar("تاريخ الميلاد"), ar("الرقم الوطني"), ar("الفوج"), ar("الاسم")]
    rows = [header]
    for st in students:
        rows.append([
            ar(st.get("notes") or ""),
            ar(st.get("phone") or ""),
            ar(st.get("birth_date") or ""),
            ar(st.get("national_id") or ""),
            ar(st.get("squad_name") or "-"),
            ar(st.get("full_name") or ""),
        ])
    if len(rows) == 1:
        rows.append([ar("لا توجد بيانات"), "", "", "", "", ""])

    table = Table(rows, colWidths=[3*cm, 2.5*cm, 2.5*cm, 3*cm, 2*cm, 4*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Arabic"),
        ("FONTNAME", (0, 0), (-1, 0), "ArabicBold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    doc.build(story)
    return path
