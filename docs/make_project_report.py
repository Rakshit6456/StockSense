"""Builds docs/StockSense_Project_Report.docx (plain, academic formatting, <=10 pages).

Run from the project root:  python3 docs/make_project_report.py
"""
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

FONT = "Times New Roman"
OUT = "docs/StockSense_Project_Report.docx"

doc = Document()

# ---------- page + base styles ----------
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)  # A4
sec.left_margin = sec.right_margin = Cm(2.54)
sec.top_margin = sec.bottom_margin = Cm(2.3)


def set_font(style, size, bold=False, italic=False):
    style.font.name = FONT
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    style.font.color.rgb = None
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if rf.get(qn(a)) is not None:
            del rf.attrib[qn(a)]
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FONT)


normal = doc.styles["Normal"]
set_font(normal, 11)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.12
normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

h1 = doc.styles["Heading 1"]
set_font(h1, 13.5, bold=True)
h1.paragraph_format.space_before = Pt(14)
h1.paragraph_format.space_after = Pt(5)
h1.paragraph_format.keep_with_next = True
h1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

h2 = doc.styles["Heading 2"]
set_font(h2, 11.5, bold=True)
h2.paragraph_format.space_before = Pt(8)
h2.paragraph_format.space_after = Pt(3)
h2.paragraph_format.keep_with_next = True
h2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

for name in ("List Bullet", "List Number"):
    set_font(doc.styles[name], 11)
    doc.styles[name].paragraph_format.space_after = Pt(2)
    doc.styles[name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


# ---------- helpers ----------
def para(text="", bold=False, italic=False, align=None, size=None, after=None, before=None):
    p = doc.add_paragraph()
    add_runs(p, text, bold, italic, size)
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    return p


def add_runs(p, text, bold=False, italic=False, size=None):
    """Supports **bold** and `code` inline markup."""
    import re
    for tok in re.split(r"(\*\*.+?\*\*|`.+?`)", text):
        if not tok:
            continue
        if tok.startswith("**"):
            r = p.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith("`"):
            r = p.add_run(tok[1:-1]); r.font.name = "Courier New"
            r._element.rPr.rFonts.set(qn("w:cs"), "Courier New")
            r.font.size = Pt(9.5)
            r.bold = bold
            continue
        else:
            r = p.add_run(tok); r.bold = bold
        r.italic = italic
        if size:
            r.font.size = Pt(size)


def bullets(items):
    for t in items:
        p = doc.add_paragraph(style="List Bullet")
        add_runs(p, t)


def heading(text, level=1):
    return doc.add_heading(text, level=level)


def shade(cell, fill):
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def table(headers, rows, widths, caption=None, size=9.5):
    if caption:
        c = para(caption, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=10, after=3, before=4)
        c.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        add_runs(cell.paragraphs[0], h, bold=True, size=size)
        shade(cell, "E7E7E7")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            add_runs(cells[i].paragraphs[0], v, size=size)
    for r in t.rows:
        for i, w in enumerate(widths):
            r.cells[i].width = Cm(w)
        for c in r.cells:
            for p in c.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.line_spacing = 1.0
    for r in t.rows[:-1]:  # keep the whole table on one page
        for c in r.cells:
            for p in c.paragraphs:
                p.paragraph_format.keep_with_next = True
    # repeat header row
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for r in t.rows:  # don't split rows across pages
        cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); r._tr.get_or_add_trPr().append(cs)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def code_block(lines):
    for ln in lines:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(ln)
        r.font.name = "Courier New"
        r._element.rPr.rFonts.set(qn("w:cs"), "Courier New")
        r.font.size = Pt(9)
    doc.paragraphs[-1].paragraph_format.space_after = Pt(6)
    doc.paragraphs[-1].paragraph_format.keep_with_next = False


def add_page_number(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        r.font.name = FONT; r.font.size = Pt(10)
        if kind:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), kind); r._r.append(f)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; r._r.append(it)


# ====================== TITLE PAGE ======================
for _ in range(5):
    para("", after=14)
para("StockSense", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=30, after=2)
para("Smart Inventory Management System", align=WD_ALIGN_PARAGRAPH.CENTER, size=16, after=26)
para("Project Report", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, after=40)

t = doc.add_table(rows=0, cols=2)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
t.autofit = False
for k, v in [
    ("Course", "[Course name and code]"),
    ("Department", "[Department], [Institute name]"),
    ("Group members", "[Member 1 – Roll no.]\n[Member 2 – Roll no.]\n[Member 3 – Roll no.]\n[Member 4 – Roll no.]"),
    ("Faculty guide", "[Teacher name]"),
    ("Submission date", "[Date]"),
]:
    cells = t.add_row().cells
    cells[0].width, cells[1].width = Cm(4.2), Cm(9)
    cells[0].text = ""; cells[1].text = ""
    add_runs(cells[0].paragraphs[0], k, bold=True, size=11.5)
    lines = v.split("\n")
    add_runs(cells[1].paragraphs[0], lines[0], size=11.5)
    for extra in lines[1:]:
        add_runs(cells[1].add_paragraph(), extra, size=11.5)
    for c in cells:
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(5)

doc.add_page_break()

# ====================== 1. PROBLEM STATEMENT ======================
heading("1. Problem Statement and Objective")
heading("1.1 Problem statement", 2)
para("Small and medium retailers, grocery shops in particular, still track stock in notebooks or "
     "spreadsheets. These methods do not warn the owner before an item runs out, give no view of which "
     "products earn the most, and leave no reliable record of who sold what and when. The usual results "
     "are lost sales from stock-outs, cash locked in slow-moving goods, and stock counts that no longer "
     "match the shelf.")
para("StockSense is a web-based inventory management system that replaces these manual methods. It keeps "
     "an accurate stock count, records every sale and purchase, and turns the transaction history into "
     "reorder suggestions and sales analytics, using only open-source tools and an embedded database so "
     "that a shop can run it on a single laptop.")
heading("1.2 Objectives", 2)
bullets([
    "Design a normalised relational schema for users, suppliers, products and transactions.",
    "Provide role-based login (admin and staff) with securely hashed passwords.",
    "Support full create, read, update and delete operations for products and suppliers.",
    "Record sales and purchases atomically so that stock can never become negative.",
    "Calculate reorder points, ABC classification, dead stock and moving-average demand.",
    "Show a dashboard and interactive charts, and export inventory and sales data to CSV.",
    "Verify all business logic with an automated test suite.",
])

# ====================== 2. SCOPE AND REQUIREMENTS ======================
heading("2. Scope and Requirements")
heading("2.1 Scope", 2)
para("**In scope:** a single-store deployment with a local SQLite database; two user roles; product, "
     "supplier, sale and purchase management; analytics computed from the stored transaction history; "
     "CSV export with filters; and a seed script that loads 30 sample grocery products and 5 suppliers.")
para("**Out of scope:** multi-store or multi-currency operation, barcode or RFID scanning, payment "
     "processing, e-mailing purchase orders, and single sign-on. Stock levels change only through "
     "recorded sales and purchases; they cannot be edited directly.")
heading("2.2 Functional requirements", 2)
table(["ID", "Requirement"], [
    ["FR-1", "Users log in with a username and password; admins and staff have different privileges."],
    ["FR-2", "Add, view, search, edit and delete products identified by a unique SKU."],
    ["FR-3", "Add, edit and delete suppliers and link them to products."],
    ["FR-4", "Record sales (stock decreases) and purchases (stock increases) with timestamp and user."],
    ["FR-5", "Reject a sale that exceeds available stock and leave no partial record behind."],
    ["FR-6", "List products whose stock is below the calculated reorder point with a suggested order quantity."],
    ["FR-7", "Provide ABC classification, dead-stock report and 7-day moving average of sales."],
    ["FR-8", "Show a dashboard: total products, stock value at cost and today's sales."],
    ["FR-9", "Export inventory and sales to CSV, applying the filters selected on screen."],
], [1.6, 14.3], caption="Table 1: Functional requirements")
heading("2.3 Non-functional requirements", 2)
table(["Quality", "Requirement"], [
    ["Security", "Passwords stored as salted PBKDF2-SHA256 hashes; CSV exports protected against formula injection."],
    ["Reliability", "Stock changes and the matching history row are written in one database transaction."],
    ["Portability", "Runs on Windows, macOS or Linux with Python 3.9+ and no database server."],
    ["Maintainability", "Business logic is separate from the user interface, and no SQL appears in the UI files."],
    ["Testability", "Backend can be tested without starting the web app, using a temporary database."],
], [3.2, 12.7], caption="Table 2: Non-functional requirements")

# ====================== 3. TECH STACK ======================
heading("3. Technology Stack and Justification")
table(["Technology", "Used for", "Why it was chosen"], [
    ["Python", "All backend logic, UI scripts and tests", "Readable, well known to the team, and has libraries for every layer of the project."],
    ["SQLite (`sqlite3`)", "Data storage", "Part of the Python standard library; no server to install; supports transactions, CHECK and foreign-key constraints."],
    ["Streamlit", "Web user interface", "Builds a browser UI directly from Python, so the whole project stays in one language; has forms, tabs, metrics and download buttons built in."],
    ["pandas", "Tabular data handling", "Quick filtering and grouping of results before display and export."],
    ["Plotly", "Interactive charts", "Hover, zoom and legend toggling with no JavaScript written; integrates with Streamlit."],
    ["hashlib / hmac", "Password security", "PBKDF2-SHA256 and constant-time comparison without adding a third-party package."],
    ["pytest", "Automated testing", "Concise tests, fixtures and parametrisation; temporary databases via environment variable."],
    ["Git / GitHub", "Collaboration", "Feature branches and pull requests let four members work on separate modules."],
], [3.2, 4.4, 8.3], caption="Table 3: Technology stack")
para("Heavier alternatives were considered. Django or Flask would have required separate HTML templates, "
     "and PostgreSQL or MySQL would need a running server; neither is justified for a single-store tool "
     "with a few thousand rows. The chosen stack keeps installation to one command "
     "(`pip install -r requirements.txt`), and the backend can be moved to a larger database later "
     "because the UI never touches SQL directly.")

# ====================== 4. IMPLEMENTATION ======================
heading("4. Implementation Details and Code Structure")
heading("4.1 Architecture", 2)
para("The application has three layers. The **presentation layer** (`app.py` and `pages/`) draws the "
     "screens and calls backend functions. The **business-logic layer** (`backend/`) contains all rules "
     "and calculations. The **data layer** is a single SQLite file (`data/inventory.db`). A test "
     "(`test_no_sql_in_ui_files`) checks that no SQL appears in the UI files, which keeps the layers apart.")
code_block([
    "StockSense/",
    "  app.py                      login, dashboard (KPI cards)",
    "  pages/",
    "    1_Products.py             products, suppliers, CSV export",
    "    2_Sales_and_Purchases.py  sales, purchases, history, CSV",
    "    3_Analytics.py            trend, ABC, dead stock, reorder",
    "    _utils.py                 session handling, auth guard, sidebar",
    "  backend/",
    "    database.py   inventory.py   auth.py   (schema, CRUD, login)",
    "    analytics.py  exports.py     reports.py   (analytics, CSV, DataFrames)",
    "  data/seed_products.py       sample data loader",
    "  tests/                      202 pytest tests",
])
heading("4.2 Database design", 2)
para("Four tables are used, with indexes on `transactions(product_id, timestamp)` and "
     "`transactions(type, timestamp)` to speed up the analytics queries.")
table(["Table", "Main columns", "Constraints"], [
    ["users", "id, username, password_hash, role", "username UNIQUE; role in ('admin','staff')"],
    ["suppliers", "id, name, phone, email", "name UNIQUE"],
    ["products", "id, sku, name, category, price, cost, stock, lead_time_days, safety_stock, supplier_id", "sku UNIQUE; price, cost, stock, lead time, safety stock all >= 0; supplier FK ON DELETE SET NULL"],
    ["transactions", "id, product_id, type, quantity, unit_price, timestamp, user_id", "type in ('SALE','PURCHASE'); quantity > 0; product FK ON DELETE CASCADE"],
], [2.6, 6.6, 6.7], caption="Table 4: Database schema")
heading("4.3 Authentication and roles", 2)
para("`backend/auth.py` stores each password as a random 16-byte salt plus a PBKDF2-SHA256 hash with "
     "200,000 iterations. At login the hash is recomputed and compared with `hmac.compare_digest`, which "
     "takes the same time whether or not the guess is close. On first run a default admin account is "
     "created. After login the user's role is kept in `st.session_state`; every page calls an auth guard "
     "first, and add, edit and delete controls are shown to admins only.")
heading("4.4 Inventory and atomic sales", 2)
para("All stock movement goes through one function, `_record()` in `backend/inventory.py`, exposed as "
     "`record_sale()` and `record_purchase()`. The stock update and the history row are written inside a "
     "single database transaction. For a sale, the update is guarded in SQL itself:")
code_block([
    "UPDATE products SET stock = stock - ?",
    " WHERE id = ? AND stock >= ?",
])
para("If no row is changed, `InsufficientStockError` is raised and the transaction is rolled back, so no "
     "history row is written. Because the check happens inside the database and not in Python, two "
     "simultaneous sales cannot both succeed on the last units. SKUs are normalised to upper case, quantity "
     "must be a positive integer, and a `timestamp` argument allows historical sales to be loaded for analysis.")
heading("4.5 Analytics engine", 2)
table(["Function", "Method"], [
    ["`calculate_reorder_point`", "ROP = ceil(average daily sales over 30 days x lead time + safety stock). Zero-sale days count in the average."],
    ["`get_reorder_list`", "Products with stock below ROP, ranked by shortage using a heap. Suggested order = max(ROP - stock, target - stock), where target = max(2 x ROP, safety stock + 10)."],
    ["`abc_analysis`", "Ranks products by revenue; class A up to 80% cumulative revenue, B up to 95%, C the rest. If total revenue is zero, all items are class C."],
    ["`dead_stock`", "Products with stock > 0 and no sale in the last N days (default 30), sorted by capital tied up (stock x cost)."],
    ["`moving_average`", "Rolling mean of daily units sold (window 7), filling days with no sales with zero."],
], [4.3, 11.6], caption="Table 5: Analytics functions in backend/analytics.py")
heading("4.6 User interface and CSV export", 2)
para("The dashboard shows total products, stock value and today's sales. The Products page offers search, "
     "category and stock-status filters (In Stock, Low Stock, Out of Stock) and tabs to add, edit or delete. "
     "The Sales & Purchases page shows the current stock and price of the selected product before a sale is "
     "confirmed and previews the stock after a restock. The Analytics page has three tabs: sales trend with "
     "moving average, ABC analysis (pie and bar charts), and dead stock with the capital it ties up.")
para("`backend/exports.py` builds inventory and sales CSV files as UTF-8 with a byte-order mark so that Excel "
     "displays them correctly. Every cell passes through `_safe_cell()`, which prefixes values starting with "
     "`=`, `+`, `-`, `@`, tab or carriage return with a tab character, so a product named `=cmd...` cannot "
     "run as a spreadsheet formula.")

# ====================== 5. TESTING ======================
heading("5. Testing and Results")
para("Tests are written with pytest. Each test uses a temporary database selected through the "
     "`INVENTORY_DB` environment variable, so tests never touch real data and do not affect each other. "
     "The backend is tested directly, without starting Streamlit.")
table(["Test file", "Tests", "What it covers"], [
    ["test_inventory.py", "16", "SKU handling, duplicates, sale and purchase effects, overselling rejected with nothing logged, cascade and set-null rules, search, dashboard figures, password login."],
    ["test_analytics.py", "20", "Reorder point formula, reorder list ordering and order quantities, ABC classes, dead stock, moving average."],
    ["test_edge_cases.py", "93", "Invalid and boundary input: zero, negative and non-integer quantities, empty or unknown SKUs, zero revenue, empty database, very large values."],
    ["test_csv_export.py", "66", "Column layout, filters, BOM encoding, profit and value calculations, formula-injection escaping."],
    ["test_ui_flow.py", "7", "Demo users, sample data, UI-facing wrappers for reorder, ABC, dead stock and trend, and the rule that UI files contain no SQL."],
    ["**Total**", "**202**", "**All passing (about 1.3 seconds on the development machine).**"],
], [3.6, 1.5, 10.8], caption="Table 6: Automated test suite")
para("**Result:** running `pytest` reports `202 passed`. The key behaviours verified were that an oversell "
     "attempt raises `InsufficientStockError` and leaves stock and history unchanged; deleting a product "
     "removes its history while deleting a supplier keeps the product; direct stock edits through "
     "`update_product` are blocked; and malicious CSV values are neutralised. Manual testing of the "
     "Streamlit screens covered login for both roles, hidden admin controls for staff, filtered exports, "
     "and the three analytics tabs using the seeded sample data.")

# ====================== 6. INDUSTRY ======================
heading("6. Real-World Industry Application and Relevance")
para("Inventory control is a core operation in retail, and the techniques in StockSense are the standard ones "
     "used by commercial systems: reorder-point replenishment, ABC (Pareto) classification, and "
     "identification of slow-moving stock. A small shop can use it directly; the same design carries over "
     "to other sectors.")
table(["Sector", "How StockSense applies"], [
    ["Grocery and general retail", "Alerts before stock-outs, dead-stock list to cut waste and discount slow lines, supplier lead times in reorder planning."],
    ["Pharmacies", "SKU tracking, audit trail of every movement, reorder points per medicine (expiry dates are a natural extension)."],
    ["Restaurants and cafes", "Ingredient stock tracking and purchase recording; moving average shows weekly demand."],
    ["Small warehouses and e-commerce sellers", "Purchase and sale history per SKU; the schema can be extended with location and batch fields."],
], [4.6, 11.3], caption="Table 7: Applicability by sector")
para("Many small businesses cannot afford enterprise inventory software, so a free, locally hosted tool that "
     "gives them the same planning metrics has practical value. The audit trail with user and timestamp "
     "on every transaction also supports reconciliation and loss detection.")

# ====================== 7. CHALLENGES ======================
heading("7. Challenges Faced and Learnings")
table(["Challenge", "How it was handled and what we learned"], [
    ["Preventing negative stock", "A check in Python before the update leaves a gap between check and write. Moving the condition into the SQL `WHERE stock >= ?` makes it a single atomic step. Lesson: enforce critical rules in the database."],
    ["SQLite accepts text in numeric columns", "SQLite's flexible typing does not reject bad values on its own, so validation was added in the application layer and tests were written for it."],
    ["Test isolation", "Early tests shared one database file and affected each other. Reading the database path from an environment variable fixed this."],
    ["CSV formula injection", "Exported text that begins with `=` or `@` can run as a formula in Excel. Researching the OWASP guidance led to the tab-prefix escaping."],
    ["Streamlit re-runs the script on every interaction", "Form state and confirmations had to be kept in `st.session_state` and `st.form` to avoid duplicate submissions."],
    ["Working as a team of four", "Splitting by module (database and inventory, analytics, UI, exports and tests) with fixed function signatures, feature branches and pull-request reviews avoided merge conflicts."],
], [4.6, 11.3], caption="Table 8: Challenges and learnings")

# ====================== 8. CONCLUSION ======================
heading("8. Conclusion and Future Scope")
heading("8.1 Conclusion", 2)
para("StockSense meets the objectives set at the start: a constrained four-table database, secure role-based "
     "login, complete product and supplier management, oversell-proof sales recording, reorder, ABC, "
     "dead-stock and moving-average analytics, a dashboard with charts, and filtered CSV export. The "
     "layered design allowed the backend to be verified by 202 automated tests that all pass. The project "
     "shows that a useful inventory tool can be built with Python and SQLite alone, and it gave the team "
     "practical experience in database design, secure coding, testing and collaborative development.")
heading("8.2 Future scope", 2)
bullets([
    "Multi-store support by adding a store identifier to products and transactions.",
    "Barcode scanning for fast SKU entry during sales and stock receipt.",
    "Automatic purchase-order generation and e-mail to suppliers when stock falls below the reorder point.",
    "Expiry-date tracking for perishable goods, with alerts for items nearing expiry.",
    "Better demand forecasting (for example ARIMA or Prophet) in place of the simple moving average.",
    "Migration to PostgreSQL and a REST API for concurrent users and mobile access; Docker deployment.",
    "Additional roles (viewer, manager) and a searchable audit-log screen.",
])

heading("References")
for r in [
    "Python Software Foundation, Python documentation, sqlite3 and hashlib modules, docs.python.org.",
    "Streamlit documentation, docs.streamlit.io; Plotly Python documentation, plotly.com/python; pytest documentation, docs.pytest.org.",
    "NIST Special Publication 800-132, Recommendation for Password-Based Key Derivation, 2010.",
    "OWASP, CSV Injection, owasp.org/www-community/attacks/CSV_Injection.",
    "F. W. Harris, \"How Many Parts to Make at Once,\" Factory, The Magazine of Management, 1913 (basis of reorder-point theory).",
]:
    p = doc.add_paragraph(style="List Number")
    add_runs(p, r, size=10.5)

# footer page numbers on all pages
add_page_number(doc.sections[0])
doc.sections[0].different_first_page_header_footer = True  # no number on title page

doc.core_properties.title = "StockSense – Project Report"
doc.core_properties.author = ""
doc.save(OUT)
print("saved", OUT)
