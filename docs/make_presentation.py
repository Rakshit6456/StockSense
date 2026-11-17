"""Builds docs/StockSense_Presentation.pptx (16:9) with python-pptx.

Needs: pip install python-pptx   |   Run from project root: python3 docs/make_presentation.py
Screenshots are read from docs/screenshots/.
"""
from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "screenshots"
OUT = ROOT / "StockSense_Presentation.pptx"

BG, INK, MUTED, LINE = "F7F5F0", "1D2B2A", "66726F", "DAD6CC"
ACCENT, ACCENT_LT, AMBER = "1F6F5B", "DCEBE5", "C97F00"
CODE_BG, CODE_FG = "17211F", "E6EDEB"
HEAD, BODY, MONO = "Georgia", "Calibri", "Courier New"


def rgb(h):
    return RGBColor(int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16))


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
_n = [0]


def rect(s, x, y, w, h, fill=None, line=None, shape=MSO_SHAPE.RECTANGLE, lw=0.75):
    r = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:
        r.fill.solid(); r.fill.fore_color.rgb = rgb(fill)
    else:
        r.fill.background()
    if line:
        r.line.color.rgb = rgb(line); r.line.width = Pt(lw)
    else:
        r.line.fill.background()
    r.shadow.inherit = False
    return r


def text(s, t, x, y, w, h, size=16, bold=False, color=INK, font=BODY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False, spacing=None):
    """t may be a string or a list of strings (one paragraph each)."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(t if isinstance(t, list) else [t]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        r = p.add_run(); r.text = line
        r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
        r.font.name = font; r.font.color.rgb = rgb(color)
    return tb


def bullets(s, items, x, y, w, size=17, gap=9, color=INK):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(0.5))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        r0 = p.add_run(); r0.text = "–  "; r0.font.size = Pt(size); r0.font.color.rgb = rgb(ACCENT)
        r0.font.bold = True; r0.font.name = BODY
        # "Lead: rest" -> bold lead
        if "::" in it:
            lead, rest = it.split("::", 1)
            r1 = p.add_run(); r1.text = lead; r1.font.bold = True
            r2 = p.add_run(); r2.text = rest
            runs = (r1, r2)
        else:
            r1 = p.add_run(); r1.text = it; runs = (r1,)
        for r in runs:
            r.font.size = Pt(size); r.font.name = BODY; r.font.color.rgb = rgb(color)
    return tb


def code(s, lines, x, y, w, h, size=12.5):
    rect(s, x, y, w, h, fill=CODE_BG)
    tb = s.shapes.add_textbox(Inches(x + 0.25), Inches(y + 0.2), Inches(w - 0.5), Inches(h - 0.4))
    tf = tb.text_frame; tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(1)
        col = CODE_FG
        if ln.strip().startswith("#"):
            col = "7FC4AE"
        r = p.add_run(); r.text = ln if ln else " "
        r.font.name = MONO; r.font.size = Pt(size); r.font.color.rgb = rgb(col)


def new_slide(section, title, notes=""):
    s = prs.slides.add_slide(BLANK)
    _n[0] += 1
    s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(BG)
    rect(s, 0, 0, 0.18, 7.5, fill=ACCENT)
    text(s, section.upper(), 0.7, 0.45, 8, 0.3, size=12, bold=True, color=ACCENT)
    text(s, title, 0.7, 0.78, 11.9, 0.9, size=32, bold=True, font=HEAD)
    text(s, "StockSense", 0.7, 7.05, 4, 0.25, size=10.5, color=MUTED)
    text(s, str(_n[0] + 1), 12.1, 7.05, 0.6, 0.25, size=10.5, color=MUTED, align=PP_ALIGN.RIGHT)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def picture(s, name, x, y, h=None, w=None, caption=None):
    kw = {}
    if h: kw["height"] = Inches(h)
    if w: kw["width"] = Inches(w)
    pic = s.shapes.add_picture(str(SHOTS / f"{name}.png"), Inches(x), Inches(y), **kw)
    pic.line.color.rgb = rgb(LINE); pic.line.width = Pt(1)
    if caption:
        text(s, caption, x, y + pic.height / 914400 + 0.1, pic.width / 914400, 0.3, size=12.5,
             color=MUTED, align=PP_ALIGN.CENTER, italic=True)
    return pic


def card(s, x, y, w, h, title, body, size=14.5, tsize=16.5, fill="FFFFFF"):
    rect(s, x, y, w, h, fill=fill, line=LINE)
    rect(s, x, y, 0.07, h, fill=ACCENT)
    text(s, title, x + 0.3, y + 0.2, w - 0.5, 0.4, size=tsize, bold=True, font=HEAD)
    text(s, body, x + 0.3, y + 0.72, w - 0.55, h - 0.85, size=size, color="38484A")


# ============ 1. TITLE ============
s = prs.slides.add_slide(BLANK); _n[0] += 0
s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(INK)
rect(s, 0, 0, 0.18, 7.5, fill=ACCENT)
text(s, "IRP-I (CSE25307)  ·  PROJECT PRESENTATION", 0.9, 0.9, 9, 0.3, size=13, bold=True, color="7FC4AE")
text(s, "StockSense", 0.9, 2.0, 9, 1.2, size=64, bold=True, font=HEAD, color="FFFFFF")
text(s, "Smart Inventory Management System", 0.9, 3.25, 10, 0.6, size=26, color="CFE3DC", font=HEAD)
text(s, "Stock tracking, reorder alerts and sales analytics for retail and grocery businesses.\n"
        "Python  ·  SQLite  ·  Streamlit", 0.9, 4.1, 9.5, 0.9, size=16, color="9FB4AF")
rect(s, 0.9, 5.25, 11.5, 0.02, fill="3A4C49")
text(s, ["Aayaan Kumar – 2581164", "Aman Shokaria – 2581179"], 0.9, 5.5, 4.5, 0.8, size=15, color="E6EDEB", spacing=3)
text(s, ["Rakshit Yadav – 2581165", "Rajveer Singh – 2581171"], 4.9, 5.5, 4.5, 0.8, size=15, color="E6EDEB", spacing=3)
text(s, ["Faculty guide", "Dr. Sapna Arora"], 9.3, 5.5, 3.5, 0.8, size=15, color="E6EDEB", spacing=3)
s.notes_slide.notes_text_frame.text = ("Introduce the group and the project in one line: StockSense is a web-based inventory "
                                       "system that tells a shop what to reorder and what is not selling.")

# ============ 2. PROBLEM ============
s = new_slide("Problem statement", "Shops lose money on stock they cannot see",
              "Spreadsheets and notebooks work until the shop grows. The three costs on the right are what the owner feels.")
text(s, "Small retailers and grocery shops still track stock in notebooks or spreadsheets. "
        "Nothing warns them before an item runs out, and nothing shows what is not selling.",
     0.7, 1.9, 5.6, 2.0, size=18, color="38484A")
text(s, "Objective", 0.7, 4.0, 5, 0.4, size=14, bold=True, color=ACCENT)
text(s, "Build a simple web system that keeps an accurate stock count, records every sale and purchase, "
        "and turns that history into reorder suggestions and sales analytics.",
     0.7, 4.4, 5.6, 2.0, size=17, bold=True, font=HEAD)
items = [("Stock-outs", "No alert before an item runs out, so sales are lost and customers leave."),
         ("Dead stock", "Slow-moving goods lock up cash and perishables go to waste."),
         ("No audit trail", "Counts drift from the shelf and nobody knows who sold what, or when.")]
for i, (t, b) in enumerate(items):
    y = 1.9 + i * 1.65
    rect(s, 7.0, y, 5.6, 1.45, fill="FFFFFF", line=LINE)
    text(s, f"0{i+1}", 7.25, y + 0.2, 0.8, 0.7, size=30, bold=True, font=HEAD, color=ACCENT)
    text(s, t, 8.2, y + 0.22, 4.2, 0.4, size=18, bold=True, font=HEAD)
    text(s, b, 8.2, y + 0.68, 4.2, 0.7, size=14.5, color="38484A")

# ============ 3. SOLUTION ============
s = new_slide("Problem statement", "What StockSense does",
              "Four things the owner gets. Each maps to a page in the app which we demo later.")
mods = [("Manage", "Products and suppliers with unique SKUs, search, filters, safety stock and lead time."),
        ("Record", "Sales and purchases update stock atomically. Overselling is rejected."),
        ("Analyse", "Reorder list, ABC classification, dead stock and 7-day moving average."),
        ("Export", "Filtered inventory and sales CSV files, safe to open in Excel.")]
for i, (t, b) in enumerate(mods):
    x = 0.7 + i * 3.05
    card(s, x, 2.0, 2.85, 2.9, t, b, size=17, tsize=19)
rect(s, 0.7, 5.35, 11.9, 1.2, fill=ACCENT_LT)
text(s, "Two roles", 1.0, 5.55, 2.2, 0.4, size=16, bold=True, font=HEAD, color=ACCENT)
text(s, "Admin can add, edit and delete products and suppliers. Staff can record sales and view reports. "
        "Passwords are stored as salted PBKDF2-SHA256 hashes.",
     3.2, 5.55, 9.1, 0.9, size=15, color=INK)

# ============ 4. ARCHITECTURE ============
s = new_slide("Technical approach", "Three layers, no SQL in the UI",
              "Layers talk only through function calls. A test checks that UI files contain no SQL.")
layers = [("Presentation", "Streamlit", ["app.py (login, dashboard)", "pages/1_Products.py", "pages/2_Sales_and_Purchases.py",
                                         "pages/3_Analytics.py"]),
          ("Business logic", "Python backend", ["inventory.py  CRUD, sales", "analytics.py  reorder, ABC", "auth.py  login, hashing",
                                                 "exports.py  CSV"]),
          ("Data", "SQLite", ["users", "suppliers", "products", "transactions"])]
for i, (t, sub, rows) in enumerate(layers):
    x = 0.7 + i * 4.15
    rect(s, x, 1.95, 3.65, 3.35, fill="FFFFFF", line=LINE)
    rect(s, x, 1.95, 3.65, 0.85, fill=ACCENT)
    text(s, t, x + 0.25, 2.07, 3.2, 0.4, size=19, bold=True, font=HEAD, color="FFFFFF")
    text(s, sub, x + 0.25, 2.47, 3.2, 0.3, size=13, color="CFE3DC")
    text(s, rows, x + 0.25, 3.05, 3.2, 2.1, size=16.5, font=MONO if i == 2 else BODY, color=INK, spacing=7)
    if i < 2:
        a = rect(s, x + 3.68, 3.3, 0.45, 0.4, fill=AMBER, shape=MSO_SHAPE.RIGHT_ARROW)
text(s, "Why this design", 0.7, 5.65, 4, 0.35, size=14, bold=True, color=ACCENT)
text(s, "The backend runs and is tested without starting the web app, and the database can be swapped later "
        "without touching the screens.", 0.7, 6.0, 11.9, 0.8, size=16, color="38484A")

# ============ 5. STACK + SCHEMA ============
s = new_slide("Technical approach", "Technology stack and database design",
              "Chosen to keep installation to one command and run on a single laptop.")
stack = [("Python", "all logic and tests"), ("SQLite", "stdlib, transactions, constraints"),
         ("Streamlit", "web UI in pure Python"), ("pandas + Plotly", "tables and interactive charts"),
         ("hashlib / hmac", "PBKDF2 password hashing"), ("pytest", "202 automated tests")]
for i, (t, b) in enumerate(stack):
    y = 1.95 + i * 0.78
    rect(s, 0.7, y, 5.5, 0.66, fill="FFFFFF", line=LINE)
    rect(s, 0.7, y, 0.07, 0.66, fill=ACCENT)
    text(s, t, 1.0, y + 0.17, 2.1, 0.35, size=15.5, bold=True)
    text(s, b, 3.1, y + 0.19, 3.0, 0.35, size=14, color=MUTED)
text(s, "Schema (4 tables)", 6.9, 1.95, 5, 0.4, size=14, bold=True, color=ACCENT)
tabs = [("users", "username UNIQUE · role admin|staff"),
        ("suppliers", "name UNIQUE · phone · email"),
        ("products", "sku UNIQUE · price, cost, stock ≥ 0 · lead time · safety stock · supplier FK"),
        ("transactions", "type SALE|PURCHASE · quantity > 0 · unit price · timestamp · user FK")]
for i, (t, b) in enumerate(tabs):
    y = 2.4 + i * 1.02
    rect(s, 6.9, y, 5.7, 0.9, fill="FFFFFF", line=LINE)
    text(s, t, 7.15, y + 0.12, 2, 0.3, size=15, bold=True, font=MONO, color=ACCENT)
    text(s, b, 7.15, y + 0.45, 5.3, 0.4, size=12.5, color="38484A")
text(s, "CHECK constraints stop negative stock or price at the database level; two indexes speed up the analytics queries.",
     6.9, 6.5, 5.7, 0.5, size=13, color=MUTED, italic=True)

# ============ 6. ANALYTICS ============
s = new_slide("Technical approach", "How the analytics work",
              "All four are computed from the transaction history, so they improve as more sales are recorded.")
cards = [("Reorder point", "ROP = ceil(avg daily sales over 30 days × lead time + safety stock). If stock is below ROP, "
                           "suggest an order up to max(2 × ROP, safety + 10)."),
         ("ABC classification", "Rank products by revenue. A: first 80% of cumulative revenue, B: next 15%, C: the rest. "
                                "Shows where to focus."),
         ("Dead stock", "Products with stock but no sale in the last N days (default 30), sorted by capital tied up "
                        "(stock × cost)."),
         ("Moving average", "Rolling mean of daily units sold (window 7), with zero-sale days included, to show the "
                            "demand trend.")]
for i, (t, b) in enumerate(cards):
    x = 0.7 + (i % 2) * 6.05
    y = 1.95 + (i // 2) * 2.45
    card(s, x, y, 5.85, 2.25, t, b, size=17.5, tsize=19)

# ============ 7. CODE: ATOMIC SALE ============
s = new_slide("Code demo", "Selling safely: stock can never go negative",
              "backend/inventory.py, function _record. The check is inside the SQL, so two simultaneous sales cannot both take the last units.")
code(s, [
    "# backend/inventory.py  ->  _record()",
    "with conn:                  # one atomic transaction",
    "    cur = conn.execute(",
    '        "UPDATE products SET stock = stock - ? "',
    '        "WHERE id = ? AND stock >= ?",',
    "        (qty, product[\"id\"], qty))",
    "    if cur.rowcount == 0:",
    "        raise InsufficientStockError(",
    '            f"Only {product[\'stock\']} units in stock")',
    "    conn.execute(\"INSERT INTO transactions ...\")",
], 0.7, 1.95, 7.3, 3.75, size=14.5)
bullets(s, ["Guarded UPDATE:: the stock check and the write are one step.",
            "Rollback:: if it fails, no history row is written.",
            "Single entry point:: stock changes only through sales and purchases."],
        8.4, 2.0, 4.3, size=16, gap=14)
code(s, ["$ pytest -q", "........................................", "202 passed in 1.3s"],
     0.7, 5.95, 7.3, 0.95, size=13.5)
text(s, "Covered by test_cannot_oversell_and_nothing_is_logged", 8.4, 6.2, 4.4, 0.5, size=13, color=MUTED, italic=True)

# ============ 8. CODE: ANALYTICS + EXPORT ============
s = new_slide("Code demo", "Reorder point and CSV protection",
              "Two short functions that carry most of the business value and the security story.")
text(s, "backend/analytics.py", 0.7, 1.9, 5, 0.3, size=13, bold=True, color=ACCENT, font=MONO)
code(s, [
    "daily = average_daily_sales(sku, days=30)",
    "rop = math.ceil(daily * lead_time_days",
    "                + safety_stock)",
    "",
    "# low stock -> suggest an order",
    "target = max(2 * rop, safety_stock + 10)",
    "qty = max(rop - stock, target - stock)",
], 0.7, 2.25, 5.85, 2.55, size=14.5)
text(s, "backend/exports.py", 6.85, 1.9, 5, 0.3, size=13, bold=True, color=ACCENT, font=MONO)
code(s, [
    'INJECT = {"=", "+", "-", "@", "\\t", "\\r"}',
    "",
    "def _safe_cell(value):",
    '    text = "" if value is None else str(value)',
    "    if text and text[0] in INJECT:",
    '        return "\\t" + text   # neutralise',
    "    return text",
], 6.85, 2.25, 5.75, 2.55, size=13.5)
card(s, 0.7, 5.15, 5.85, 1.55, "Result", "Items below their reorder point appear on the dashboard with a suggested order quantity.", size=16)
card(s, 6.85, 5.15, 5.75, 1.55, "Result", "A product named =cmd|... is exported as plain text and cannot run as an Excel formula.", size=16)

# ============ 9. DEMO: LOGIN + DASHBOARD ============
s = new_slide("Code demo  ·  live app", "Login and dashboard",
              "Demo: log in as admin. The dashboard shows total products, stock value, today's sales and the Reorder Now list.")
picture(s, "login", 0.7, 1.85, h=4.35, caption="Role-based login (admin / staff)")
picture(s, "dashboard", 6.75, 1.85, h=4.35, caption="Dashboard: KPIs and Reorder Now list")
text(s, "Staff accounts do not see the add, edit and delete controls.", 0.7, 6.65, 11.9, 0.3, size=14, color=MUTED)

# ============ 10. DEMO: PRODUCTS + SALES ============
s = new_slide("Code demo  ·  live app", "Products and sales",
              "Demo: filter products, then record a sale. Try selling more than the stock to show the error.")
picture(s, "products", 0.7, 1.85, h=4.35, caption="Products catalog: search, filters, CSV export")
picture(s, "sales", 6.75, 1.85, h=4.35, caption="Record a sale: stock shown before confirming")
text(s, "Selling more than the available stock is rejected and nothing is logged.", 0.7, 6.65, 11.9, 0.3, size=14, color=MUTED)

# ============ 11. DEMO: ANALYTICS ============
s = new_slide("Code demo  ·  live app", "Analytics: trend and ABC",
              "Demo: switch the moving-average window; open the ABC tab and point out that 13 items give about 79% of revenue.")
picture(s, "analytics_trend", 0.7, 1.85, h=4.35, caption="Sales volume with 7-day moving average")
picture(s, "analytics_abc", 6.75, 1.85, h=4.35, caption="ABC revenue classification (Pareto)")
text(s, "In the demo data, 13 class-A items bring in about 79% of revenue.", 0.7, 6.65, 11.9, 0.3, size=14, color=MUTED)

# ============ 12. DEMO: DEAD STOCK ============
s = new_slide("Code demo  ·  live app", "Analytics: dead stock",
              "Capital tied up is stock multiplied by cost. This is what an owner would act on: discount or stop reordering.")
picture(s, "analytics_dead", 0.7, 1.85, h=4.85)
bullets(s, ["19 products:: have not sold in the last 30 days.",
            "₹116,550:: of working capital is tied up in them.",
            "Sorted by capital:: so the biggest problems come first.",
            "Adjustable window:: slider changes the inactivity threshold."],
        7.9, 2.0, 4.8, size=17, gap=16)

# ============ 13. TESTING ============
s = new_slide("Technical approach", "Testing: 202 automated tests, all passing",
              "Each test uses a temporary database chosen through an environment variable, so tests never touch real data.")
text(s, "202", 0.7, 1.9, 4, 1.6, size=96, bold=True, font=HEAD, color=ACCENT)
text(s, "tests passed in about 1.3 seconds", 0.7, 3.55, 4.5, 0.4, size=18, color=INK)
text(s, "Each test runs on its own temporary database, so no test affects another or real data.",
     0.7, 4.15, 4.4, 1.2, size=15, color="38484A")
rows = [("test_edge_cases", 93), ("test_csv_export", 66), ("test_analytics", 20), ("test_inventory", 16), ("test_ui_flow", 7)]
for i, (n, c) in enumerate(rows):
    y = 2.0 + i * 0.92
    text(s, n, 5.9, y + 0.1, 2.6, 0.4, size=15, font=MONO)
    rect(s, 8.5, y + 0.05, 3.3 * c / 93, 0.45, fill=ACCENT)
    text(s, str(c), 8.5 + 3.3 * c / 93 + 0.12, y + 0.08, 0.7, 0.4, size=15, bold=True)
text(s, "Covered: boundary input, oversell rejection, cascade rules, formulas, CSV escaping.",
     5.9, 6.6, 6.8, 0.4, size=13, color=MUTED, italic=True)

# ============ 14. INDUSTRY ============
s = new_slide("Industry relevance", "The same techniques run real retail",
              "Reorder points, ABC analysis and dead-stock review are standard in commercial systems. The difference here is cost and setup.")
ind = [("Grocery and retail", "Reorder alerts before stock-outs; dead-stock list to discount slow lines and cut waste."),
       ("Pharmacies", "Per-SKU tracking and an audit trail of every movement; expiry dates are a natural extension."),
       ("Restaurants and cafes", "Ingredient stock and purchase recording; moving average shows weekly demand."),
       ("Small warehouses, e-commerce", "Purchase and sale history per SKU; schema extends to locations and batches.")]
for i, (t, b) in enumerate(ind):
    x = 0.7 + (i % 2) * 6.05
    y = 1.95 + (i // 2) * 1.95
    card(s, x, y, 5.85, 1.75, t, b, size=16.5, tsize=18)
rect(s, 0.7, 5.95, 11.9, 0.85, fill=ACCENT_LT)
text(s, "Many small businesses cannot afford enterprise software. A free, locally hosted tool gives them the same "
        "planning metrics.", 1.0, 6.12, 11.3, 0.6, size=16, bold=True, font=HEAD, color=INK)

# ============ 15. CONCLUSION ============
s = new_slide("Conclusion", "What we delivered and where it goes next",
              "Close with the learning: critical rules belong in the database, and separating layers made testing easy.")
text(s, "Delivered", 0.7, 1.95, 5, 0.4, size=14, bold=True, color=ACCENT)
bullets(s, ["Secure login:: with admin and staff roles.",
            "Atomic sales:: stock can never go negative.",
            "Analytics:: reorder, ABC, dead stock, moving average.",
            "Dashboard and CSV export:: with formula-injection protection.",
            "202 passing tests:: on a layered, maintainable codebase."],
        0.7, 2.4, 5.8, size=18, gap=12)
text(s, "Future scope", 7.0, 1.95, 5, 0.4, size=14, bold=True, color=ACCENT)
bullets(s, ["Multi-store support and barcode scanning",
            "Automatic purchase orders emailed to suppliers",
            "Expiry-date tracking for perishables",
            "Better forecasting (ARIMA, Prophet)",
            "PostgreSQL, REST API and Docker deployment"],
        7.0, 2.4, 5.6, size=18, gap=12)
rect(s, 0.7, 6.0, 11.9, 0.8, fill=INK)
text(s, "Lesson: enforce critical rules in the database, and keep business logic apart from the screens.",
     1.0, 6.2, 11.3, 0.5, size=16, bold=True, font=HEAD, color="FFFFFF")

# ============ 16. THANK YOU ============
s = prs.slides.add_slide(BLANK)
s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(INK)
rect(s, 0, 0, 0.18, 7.5, fill=ACCENT)
text(s, "Thank you", 0.9, 2.6, 10, 1.2, size=60, bold=True, font=HEAD, color="FFFFFF")
text(s, "Questions?", 0.9, 3.9, 10, 0.6, size=26, color="CFE3DC", font=HEAD)
text(s, "StockSense  ·  Aayaan Kumar, Aman Shokaria, Rakshit Yadav, Rajveer Singh", 0.9, 6.5, 11, 0.4, size=14, color="9FB4AF")

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
