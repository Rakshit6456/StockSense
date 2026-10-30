"""Generates docs/StockSense_Team_Roles.pdf (simple task sheet for the 4 team members)."""
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

OUT = os.path.join(os.path.dirname(__file__), "StockSense_Team_Roles.pdf")
ss = getSampleStyleSheet()
title = ParagraphStyle("t", parent=ss["Title"], fontSize=24, spaceAfter=6)
sub = ParagraphStyle("s", parent=ss["Normal"], fontSize=11, textColor=colors.grey,
                     alignment=1, spaceAfter=14)
h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=17, spaceBefore=4, spaceAfter=4)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=3)
body = ParagraphStyle("b", parent=ss["Normal"], fontSize=11, leading=15)
bullet = ParagraphStyle("bl", parent=body, leftIndent=14, bulletIndent=2, spaceAfter=2)

PEOPLE = [
    {
        "name": "Person 1: Database and Core Logic",
        "files": "backend/database.py, backend/inventory.py, backend/auth.py",
        "goal": "Build the foundation: where data is stored and how stock changes.",
        "tasks": [
            "Create the GitHub repo and add everyone (DONE: project skeleton is ready).",
            "Design the database tables: users, suppliers, products, transactions (DONE).",
            "Write add / edit / delete / search for products and suppliers (DONE).",
            "Write record_sale and record_purchase so stock updates automatically (DONE).",
            "Write login (admin / staff) (DONE).",
            "Review and merge teammates' pull requests; fix merge problems.",
        ],
        "present": "Problem statement, system architecture, database design.",
    },
    {
        "name": "Person 2: Analytics Engine",
        "files": "backend/analytics.py, tests/test_analytics.py",
        "goal": "Make the system smart: tell the owner what to reorder and what is not selling.",
        "tasks": [
            "average_daily_sales: units sold per day over the last 30 days.",
            "calculate_reorder_point: average daily sales x lead time + safety stock.",
            "get_reorder_list: products below their reorder point, most urgent first "
            "(use heapq / priority queue).",
            "abc_analysis: sort products by revenue; label A (top 80%), B (next 15%), C (rest).",
            "dead_stock: products in stock with no sale in the last N days.",
            "moving_average: 7-day moving average of daily sales for one product.",
            "Write pytest tests for each function with small hand-calculated examples.",
        ],
        "present": "Algorithms and data structures used (heap, sorting, hash map) with the formulas.",
    },
    {
        "name": "Person 3: Frontend (Streamlit UI)",
        "files": "app.py, pages/",
        "goal": "Make everything usable through clean screens.",
        "tasks": [
            "Dashboard: cards (total products, stock value, today's sales) and a Reorder Now list.",
            "Products page: table with search, plus forms to add / edit / delete.",
            "Sales and Purchases page: pick product by SKU, enter quantity, submit; "
            "show friendly errors (e.g. not enough stock).",
            "Analytics page: charts for sales trend, ABC classes, dead stock table.",
            "Hide admin-only actions from staff users.",
            "Use the backend functions listed in README.md; do not write SQL in the UI.",
        ],
        "present": "Live demo and user flow.",
    },
    {
        "name": "Person 4: Testing, Data, Reports and Documents",
        "files": "tests/, data/, backend/reports.py, docs/",
        "goal": "Prove it works, fill it with data, and write everything up.",
        "tasks": [
            "Make sample data: ~20 products and a few hundred sales over 60 days "
            "(load it with record_sale(..., timestamp=...)).",
            "Write extra pytest tests for edge cases (empty database, zero stock, bad input).",
            "CSV export for inventory and sales (PDF export if time allows).",
            "Write the project report (max 10 pages): problem, scope, tech stack, "
            "implementation, testing and results, industry use, challenges, future scope.",
            "Build the presentation slides (clean, few words, no clutter).",
            "Keep a record of test results and screenshots for the report.",
        ],
        "present": "Testing and results, industry relevance, conclusion and future scope.",
    },
]


def person_block(p):
    items = [Paragraph(p["name"], h1),
             Paragraph(f"<b>Your files:</b> {p['files']}", body),
             Paragraph(f"<b>Goal:</b> {p['goal']}", body),
             Paragraph("What you need to do", h2)]
    items += [Paragraph(t, bullet, bulletText="•") for t in p["tasks"]]
    items += [Paragraph("What you present", h2), Paragraph(p["present"], body)]
    return items


def main():
    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            title="StockSense Team Roles", author="StockSense Team")
    s = [Paragraph("StockSense", title),
         Paragraph("Team roles and tasks: who does what", sub),
         Paragraph("StockSense is a Python inventory system. It tracks stock, warns the owner "
                   "when to reorder, and shows which products sell well or not at all. "
                   "We use Python, SQLite and Streamlit, all in one GitHub repo.", body),
         Spacer(1, 10)]

    rows = [["Person", "Job in one line", "Main files"]]
    short = ["Database and core logic", "Analytics: reorder, ABC, dead stock",
             "Streamlit screens", "Tests, data, report, slides"]
    for p, sh in zip(PEOPLE, short):
        rows.append([p["name"].split(":")[0].split(" - ")[0], sh, p["files"]])
    t = Table(rows, colWidths=[3 * cm, 6 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")]),
    ]))
    # Wrap long cells
    cell = ParagraphStyle("c", parent=body, fontSize=9, leading=11)
    t._cellvalues = [[Paragraph(str(c), cell) if i else c for c in r]
                     for i, r in enumerate(t._cellvalues)]
    s += [t, Spacer(1, 14), Paragraph("Rules for everyone", h2)]
    for r in ["Never push to <b>main</b>. Work on your own branch "
              "(feature/analytics, feature/ui, ...), then open a pull request.",
              "Another teammate reviews each pull request before it is merged.",
              "Run <b>git pull origin main</b> every day.",
              "Comment your code. Be ready to explain ANY part of the project in Q&amp;A.",
              "Everyone speaks in the presentation."]:
        s.append(Paragraph(r, bullet, bulletText="•"))
    s.append(PageBreak())

    for i, p in enumerate(PEOPLE):
        s.append(KeepTogether(person_block(p)))
        s.append(Spacer(1, 16))
        if i == 1:
            s.append(PageBreak())

    s += [PageBreak(), Paragraph("Timeline (presentations start 5 Nov)", h1)]
    tl = [["Date", "What happens"],
          ["29 Oct", "Repo set up, everyone clones it, read README.md"],
          ["30 Oct", "P2 reorder + ABC | P3 login and layout | P4 sample data"],
          ["31 Oct", "P2 dead stock + moving average | P3 product and sales pages | P4 tests"],
          ["1 Nov", "Connect UI to backend, fix bugs together"],
          ["2 Nov", "Alerts, charts, dashboard polish, exports. P4 drafts report"],
          ["3 Nov", "Feature freeze. Full testing. Report and slides finished"],
          ["4 Nov", "Rehearse demo twice, assign speaking parts, record a backup video"],
          ["5 Nov", "Presentation"]]
    tl = [[Paragraph(str(c), cell) for c in r] for r in tl]
    tt = Table(tl, colWidths=[2.5 * cm, 14.5 * cm])
    tt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9e6f2")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    s.append(tt)
    doc.build(s)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
