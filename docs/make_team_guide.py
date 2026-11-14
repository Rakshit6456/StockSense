"""Generates docs/StockSense_Team_Guide.pdf AND docs/StockSense_Team_Guide.docx from one shared content list.

Run from the project root:  python3 docs/make_team_guide.py
Edit the CONTENT section below, then re-run to refresh both files.
"""
import os
from html.parser import HTMLParser

DOCS = os.path.dirname(os.path.abspath(__file__))
PDF_OUT = os.path.join(DOCS, "StockSense_Team_Guide.pdf")
DOCX_OUT = os.path.join(DOCS, "StockSense_Team_Guide.docx")
NAVY_HEX = "1F4E79"

# ====================================================================== CONTENT
# Blocks are plain tuples so the same content feeds both renderers.
# Inline markup allowed in text: <b>, <i>, <font face='Courier'>, <br/>, &amp; &lt; &gt;
title, sub, h1, h2, body, code, say = "title", "sub", "h1", "h2", "body", "code", "say"


def P(text, st=body):
    return ("p", text, st)


def B(items):
    return [("bul", i) for i in items]


def table(rows, widths):
    return ("table", rows, widths)


def qa(pairs):
    return table([["If the teacher asks...", "Answer in simple words"]] + [[q, a] for q, a in pairs], [6, 11])


def note(text, bg="#fff8e1"):
    return ("note", text, bg)


def SP(n=8):
    return ("space", n)


PB = ("pb",)

S = []

# ---------------------------------------------------------------- cover
S += [SP(80), P("StockSense", title),
      P("Team Guide: what each of us built, why, and how we present it", sub),
      P("Smart Inventory Management System (Python, SQLite, Streamlit)", sub),
      P("Updated 13 Nov 2026 to match the code on GitHub (main branch, 202 passing tests)", sub), SP(24),
      P("<b>Why this document exists.</b> The teacher can ask any of us about any part of the project. "
        "This guide lets all 4 of us understand every part: what it does, <i>why</i> it was built that way, "
        "and how to answer questions about it. It ends with a presentation script (skit) where each person speaks, "
        "and a rapid-fire question sheet."),
      P("<b>How to use it:</b> everyone reads every section (about 20 minutes), then practises the skit twice. "
        "Do not memorise your own part only."),
      SP(8),
      table([["Section", "What is in it"],
             ["1. Big picture", "The problem, how the pieces fit together, honest status"],
             ["2. Person 1", "Database and core logic"],
             ["3. Person 2", "Analytics engine (reorder, ABC, dead stock, moving average)"],
             ["4. Person 3", "Streamlit user interface"],
             ["5. Person 4", "Sample data, CSV export, tests, report and slides"],
             ["6. The skit", "Speaking script for all 4, with timings"],
             ["7. Rapid-fire", "Questions anyone might get, with answers"],
             ["8. Last checklist", "What is still left to do"]], [4, 13]),
      PB]

# ---------------------------------------------------------------- 1 big picture
S += [P("1. The big picture", h1),
      P("<b>The problem.</b> Small shops and warehouses track stock in notebooks or spreadsheets. "
        "Popular items run out without anyone noticing (lost sales), slow items pile up (money stuck on shelves), "
        "and the owner cannot easily see which products earn the most. Enterprise software like SAP is too "
        "expensive and complex for them."),
      P("<b>Our solution.</b> StockSense records every sale and purchase, keeps stock numbers correct automatically, "
        "warns the owner what to reorder and when, and shows which products are best sellers and which are dead stock."),
      P("How the pieces connect", h2),
      P("User (admin / staff)  -->  Streamlit pages (Person 3)  -->  backend.inventory + backend.auth (Person 1)  "
        "-->  SQLite database<br/>"
        "Analytics (Person 2) reads the transaction history and returns answers to the UI.<br/>"
        "CSV export, sample data, tests, slides and report (Person 4) wrap around everything.", code),
      P("One rule makes this clean: <b>the UI never writes SQL.</b> It only calls backend functions. That separation "
        "is what lets 4 people work in parallel on different files without breaking each other's code."),
      P("Who owns what", h2),
      table([["Person", "Area", "Files"],
             ["1", "Database and core logic", "backend/database.py, inventory.py, auth.py, tests/test_inventory.py"],
             ["2", "Analytics engine", "backend/analytics.py, tests/test_analytics.py"],
             ["3", "User interface", "app.py, pages/ (including pages/_utils.py), tests/test_ui_flow.py"],
             ["4", "Data, export, tests, report, slides", "data/seed_products.py, backend/exports.py, "
                                                          "tests/test_edge_cases.py, tests/test_csv_export.py, "
                                                          "docs/build_presentation.py"]], [1.5, 5, 10.5]),
      P("Honest status (as of 13 Nov 2026)", h2),
      table([["Part", "Status"],
             ["Person 1: database and logic", "Done and pushed. 16 tests."],
             ["Person 2: analytics", "Done and merged (pull request #1, 3 Nov). All five functions in the real "
                                     "backend/analytics.py, 20 tests. The UI now uses it."],
             ["Person 3: UI", "Done and pushed. Dashboard and 3 pages, 7 tests. CSV export buttons on the Products "
                              "and Sales pages were added by Person 4."],
             ["Person 4: data, export, tests, slides", "Partly done (pushed 6 Nov). Delivered: seed script "
                                                       "(30 products, 5 suppliers), CSV export, 159 tests, and a script "
                                                       "that builds the slides and a PDF report."],
             ["All together", "202 tests, all passing."]], [5, 12]),
      note("<b>Open issues found when reviewing the latest code:</b><br/>"
           "1. The seed script adds products and suppliers but <b>no sales history</b>, so the ABC, trend and dead-stock "
           "screens would look empty. Sales data over about 60 days is still needed.<br/>"
           "2. docs/build_presentation.py needs <font face='Courier'>python-pptx</font>, which is missing from "
           "requirements.txt (and not installed on this computer), so the slides cannot be generated on a fresh "
           "machine until it is added.<br/>"
           "3. The old stand-in analytics code is still inside pages/_utils.py. It never runs now that the real "
           "analytics exists, so it is dead code and should be deleted.<br/>"
           "4. Person 4's commits show the author name 'Your Name'. Run <font face='Courier'>git config user.name</font> "
           "and <font face='Courier'>user.email</font> so each person's contribution is visible in the history."),
      PB]

# ---------------------------------------------------------------- 2 Person 1
S += [P("2. Person 1: Database and core logic", h1),
      P("<b>Job in one line:</b> make sure the data is stored safely and stock numbers can never be wrong."),
      P("What was built", h2)]
S += B(["<b>database.py:</b> the SQLite schema with 4 tables: <b>users</b>, <b>suppliers</b>, <b>products</b>, "
        "<b>transactions</b>. Indexes on (product, time) and (type, time) so analytics queries stay fast.",
        "<b>inventory.py:</b> add / edit / delete / search products and suppliers; <b>record_sale</b> and "
        "<b>record_purchase</b>; transaction history; dashboard summary numbers; a SKU lookup dictionary.",
        "<b>auth.py:</b> user accounts and login for two roles, admin and staff.",
        "<b>tests/test_inventory.py:</b> 16 tests (overselling, bad quantities, duplicates, deletes, login)."])
S += [P("Why it was built this way (the thinking)", h2),
      table([["Decision", "Why", "What we did NOT choose"],
             ["SQLite", "Built into Python, no server to install, one file, perfect for a prototype. "
                        "Easy to move to PostgreSQL later.", "MySQL/PostgreSQL: needs a server, too heavy for "
                                                               "a 1-week project."],
             ["Database rules (CHECK, UNIQUE, FOREIGN KEY)", "The database itself refuses bad data: stock "
                                                              "cannot go negative, SKU must be unique, price "
                                                              "cannot be negative. Even a bug in our code cannot "
                                                              "corrupt it.", "Trusting only Python checks."],
             ["Stock changes only through sales/purchases", "Every change leaves a history row, so the numbers "
                                                            "can always be explained and audited.",
              "Letting users type a new stock number directly."],
             ["Atomic transaction in record_sale", "Reducing stock and writing the history row happen together "
                                                   "or not at all. If anything fails, nothing changes.",
              "Two separate steps that could leave stock and history out of sync."],
             ["Guarded UPDATE: 'stock = stock - qty WHERE stock &gt;= qty'", "Even if two people sell the last "
                                                                            "units at the same instant, stock "
                                                                            "can never go below 0.",
              "Read stock, check in Python, then write (a race condition)."],
             ["Password hashing: PBKDF2-SHA256, 200,000 rounds, random salt", "We never store the real "
                                                                              "password. Salt makes two users "
                                                                              "with the same password look "
                                                                              "different. Slow hashing makes "
                                                                              "guessing expensive.",
              "Plain text or a single fast hash."],
             ["SKU dictionary (hash map)", "Looking up a product by SKU is O(1), like a phone book by name.",
              "Scanning the whole list each time (O(n))."],
             ["Foreign keys: delete supplier -&gt; product kept (supplier set to NULL); delete product -&gt; its "
              "history is removed", "Removing a supplier should not destroy product data; a deleted product's "
                                    "history has no meaning.", "Blocking deletes or leaving orphan rows."]],
            [4.2, 8, 4.8]),
      P("How a sale works, step by step", h2),
      P("1. UI calls record_sale('RICE01', 3).<br/>"
        "2. SKU is upper-cased and the product is looked up. Quantity must be a positive whole number.<br/>"
        "3. One database transaction starts: UPDATE stock only if enough units exist; if 0 rows changed, raise "
        "InsufficientStockError and stop.<br/>"
        "4. Insert a SALE row (product, quantity, price at that moment, timestamp).<br/>"
        "5. Commit. Both changes are saved together.", code),
      P("The price is saved <i>on the transaction</i> so old sales keep their original price even if the product "
        "price changes later. That is why revenue reports stay correct."),
      P("Questions Person 1 may get (and everyone else should know)", h2),
      qa([("Why SQLite and not a bigger database?",
           "No server, built into Python, enough for a prototype. In production we would move to PostgreSQL; only "
           "database.py would need to change."),
          ("What stops stock going negative?",
           "Two layers: the code only updates if stock &gt;= quantity, and the database has a CHECK (stock &gt;= 0) rule."),
          ("What is a transaction (atomicity)?",
           "A group of steps that all succeed or all fail. Stock update plus history row are one group."),
          ("How are passwords stored?",
           "As a salted PBKDF2-SHA256 hash, never as text. Login re-hashes the typed password and compares."),
          ("Which data structure is the SKU index?",
           "A Python dict (hash map): SKU to product, lookup in O(1)."),
          ("Why can't I edit stock directly?",
           "To keep history trustworthy. Every unit that moved has a sale or purchase record.")]),
      PB]

# ---------------------------------------------------------------- 3 Person 2
S += [P("3. Person 2: Analytics engine", h1),
      P("<b>Job in one line:</b> turn raw sales history into decisions: what to reorder, what sells, what is stuck."),
      note("<b>Status:</b> done and merged (pull request #1). Everything below describes the real code in "
           "backend/analytics.py, backed by 20 tests in tests/test_analytics.py. The UI calls these functions directly.",
           "#e8f5e9"),
      P("The functions and the reasoning", h2),
      table([["Function", "What it answers", "How it works (as coded)"],
             ["average_daily_sales(sku, days=30)", "How fast does this product sell?",
              "Units sold in the last 30 days divided by 30. Quiet days count as 0."],
             ["calculate_reorder_point(sku)", "At what stock level must I reorder?",
              "average daily sales x lead time + safety stock, rounded UP (math.ceil) so we never under-order."],
             ["get_reorder_list()", "What needs ordering, most urgent first?",
              "Products with stock <b>below</b> the reorder point. Pushed on a heap (heapq) keyed by the shortage, so "
              "the biggest shortage comes out first. Also suggests an order quantity (see below)."],
             ["abc_analysis()", "Which products make the money?",
              "Sort all products by revenue, track the cumulative %: A up to 80%, B up to 95%, C the rest. "
              "Products with no revenue are C."],
             ["dead_stock(days=30)", "What is sitting unsold?",
              "Stock &gt; 0 and no sale in the last N days. Shows money tied up (stock x cost) and the last sale "
              "date, biggest amount first."],
             ["moving_average(sku, window=7)", "Is demand going up or down?",
              "Daily units from the first to the last sale date, quiet days counted as 0, then the average of "
              "the last 7 days."]],
            [4.6, 4.4, 8]),
      P("Suggested order quantity (the 'order-up-to' rule)", h2),
      P("target stock = max(2 x reorder point, safety stock + 10)<br/>"
        "suggested order = max(shortage, target stock - current stock)<br/>"
        "Idea: order enough to get back to a comfortable level, so we do not have to reorder every day.", code),
      P("Worked examples (be able to do these on the board)", h2),
      P("<b>Reorder point.</b> Rice sells 15 units/day, supplier takes 3 days, safety stock is 20.<br/>"
        "reorder point = 15 x 3 + 20 = <b>65</b>. When stock falls below 65, reorder.<br/>"
        "Why: during the 3 days we wait for delivery we will sell about 45; the extra 20 is a cushion for a busy "
        "week or a late truck.", code),
      P("<b>ABC analysis.</b> Revenues 500, 300, 100, 60, 40 (total 1000).<br/>"
        "Cumulative %: 50, 80, 90, 96, 100.<br/>"
        "Classes: product 1 = A, product 2 = A (80% is still A), product 3 = B, products 4 and 5 = C.<br/>"
        "Meaning: 2 of 5 products give 80% of revenue. Guard those closely; do not waste effort on C items.", code),
      P("<b>Moving average (window 3).</b> Daily units 4, 6, 0, 9 (the 0 is a quiet day).<br/>"
        "Averages: 4.0, 5.0, 3.33, 5.0. Counting the quiet day as 0 keeps the average honest.", code),
      P("Data structures and algorithms to mention", h2)]
S += B(["<b>Priority queue / heap (heapq):</b> pops the most urgent item first in O(log n).",
        "<b>Sorting:</b> ABC analysis sorts by revenue, O(n log n).",
        "<b>Hash map (dict):</b> per-product revenue totals while scanning transactions once, O(n).",
        "<b>Sliding window:</b> moving average keeps only the last 7 values."])
S += [note("<b>Details worth knowing for Q&amp;A:</b> the alert is strictly <i>below</i> the reorder point (stock equal to "
           "the reorder point does not alert yet); the reorder point is rounded up; times are compared in UTC; "
           "the heap ranks by shortage in units, not by days of cover left."),
      P("Questions Person 2 may get", h2),
      qa([("Why a safety stock?", "Demand and delivery times vary. Safety stock is a buffer so we do not run out "
                                  "while waiting."),
          ("Why round the reorder point up?", "Ordering slightly too much is safer than running out."),
          ("Why a heap for the reorder list?", "We always want the most urgent item first. A heap gives it in "
                                               "O(log n) without re-sorting everything."),
          ("What does ABC analysis tell the owner?", "Where the money is: protect A items, review B, relax on C. "
                                                    "It is the Pareto (80/20) principle."),
          ("Is this machine learning?", "No. It is rule-based logic and simple statistics (averages), chosen so the "
                                        "result is explainable and needs no training data."),
          ("What if a product has no sales?", "Average daily sales is 0, so the reorder point equals the safety stock; "
                                              "if it also has stock, it shows up as dead stock."),
          ("How would you improve it?", "Seasonality, exponential smoothing, or a forecasting model once we "
                                        "have months of real data.")]),
      PB]

# ---------------------------------------------------------------- 4 Person 3
S += [P("4. Person 3: The user interface (Streamlit)", h1),
      P("<b>Job in one line:</b> turn the backend into screens a shop owner can actually use, without writing any SQL."),
      P("What was built", h2)]
S += B(["<b>app.py:</b> login screen and the dashboard: summary cards (products, stock value, today's sales), a "
        "<b>Reorder Now</b> list, and recent transactions.",
        "<b>1_Products.py:</b> product catalogue with search, category, stock-status and supplier filters; "
        "admin-only tabs to add, edit and delete; an Export CSV button (added by Person 4).",
        "<b>2_Sales_and_Purchases.py:</b> record a sale or purchase by SKU, shows current stock and the stock after the "
        "change, friendly error messages, a transaction audit log, and a sales CSV export with date, product and "
        "category filters (added by Person 4).",
        "<b>3_Analytics.py:</b> three tabs: sales trend (with moving average), ABC classification (pie and bar "
        "charts), dead stock (with money tied up).",
        "<b>_utils.py:</b> shared code: login check, role check, sidebar and a demo data loader.",
        "<b>tests/test_ui_flow.py:</b> 7 tests, including one that checks the UI files contain no SQL."])
S += [P("Why it was built this way (the thinking)", h2),
      table([["Decision", "Why"],
             ["Streamlit (Python only)", "The whole project stays in Python. Forms, tables and charts need no HTML, "
                                         "CSS or JavaScript. A polished demo in days, not weeks."],
             ["No SQL in the UI", "Clean architecture: UI calls backend functions only. If the database changes, "
                                  "the UI does not break, and each person can work on their own layer."],
             ["Session state for login", "Streamlit re-runs the script on every click, so the logged-in user and "
                                         "role are kept in st.session_state."],
             ["Two roles", "Admin can manage the catalogue; staff cannot. This mirrors real shops, where not "
                           "everyone should delete products."],
             ["Stand-in analytics (now unused)", "While analytics.py was empty, the UI had its own temporary "
                                                 "calculations so the Analytics page still worked. Now that the real "
                                                 "analytics is merged, that code never runs and should be removed."],
             ["Plotly charts", "Interactive (hover, zoom) with very little code."],
             ["Demo data loader", "Fills the app with 12 products and 23 sales so a demo never starts from an "
                                  "empty screen."]], [4.5, 12.5]),
      P("What the user sees (the user flow)", h2),
      P("Login  -->  Dashboard (cards + Reorder Now)  -->  Products / Sales and Purchases / Analytics  -->  "
        "every sale or purchase updates stock and the dashboard.", code),
      P("Demo logins: <b>admin / admin123</b> (full access) and <b>staff / staff123</b> (limited). These are demo "
        "accounts only; mention in Q&amp;A that a real deployment would force a password change."),
      P("Questions Person 3 may get", h2),
      qa([("Why Streamlit and not Flask or Django?", "Faster for data dashboards and all-Python. Flask/Django "
                                                     "would be the next step for a custom front end or public API."),
          ("Where is the business logic?", "In backend/. The UI only collects input and shows results."),
          ("How does role-based access work?", "Login stores the role in session state; pages check it and "
                                               "hide admin actions from staff."),
          ("What happens if I sell more than we have?", "The backend raises InsufficientStockError and the UI "
                                                        "shows a friendly message; nothing is saved."),
          ("Where do the Analytics charts get their numbers?", "From backend/analytics.py (Person 2). The UI only "
                                                               "draws them."),
          ("How would this scale?", "Move SQLite to PostgreSQL, deploy Streamlit on a server, add a REST API.")]),
      PB]

# ---------------------------------------------------------------- 5 Person 4
S += [P("5. Person 4: Sample data, CSV export, tests, report and slides", h1),
      P("<b>Job in one line:</b> prove it works, give it realistic data, let the owner take data out, and "
        "communicate it clearly."),
      note("<b>Status:</b> partly done. Pushed on 6 Nov: the seed script, the CSV export, 159 tests, and the script "
           "that builds the slides and report. Still open: sales history data, python-pptx in requirements.txt, and "
           "the finished slides and report.", "#fff8e1"),
      P("What exists now and what is left", h2),
      table([["Deliverable", "What exists now", "Still to do"],
             ["Sample data<br/>data/seed_products.py",
              "30 grocery products and 5 suppliers (dairy, snacks, pulses, grains, beverages...). Safe to run "
              "again (skips existing). Random but reproducible stock, lead time and safety stock (fixed seed 42).",
              "Add sales history over about 60 days with <font face='Courier'>record_sale(..., timestamp=...)</font>: "
              "fast sellers, slow sellers and 2 or 3 products that never sell, so ABC, trend and dead stock all show "
              "something."],
             ["CSV export<br/>backend/exports.py",
              "<font face='Courier'>inventory_csv()</font> and <font face='Courier'>sales_csv()</font> with filters, "
              "used by download buttons on the Products and Sales pages. Includes inventory value and profit columns.",
              "Nothing required. Be ready to explain the two safety features (see Q&amp;A)."],
             ["Tests<br/>tests/",
              "93 edge-case tests and 66 CSV tests (159 total). Whole project: 202 tests, all passing.",
              "Take a screenshot of the pytest result for the report."],
             ["Slides and report<br/>docs/build_presentation.py",
              "A script that builds the PowerPoint slides and a PDF project report.",
              "Add python-pptx to requirements.txt, run the script, read the output, check the report is "
              "10 pages or fewer, and commit the finished files."]], [3.4, 7, 6.6]),
      P("Results to put in the report (these are real)", h2)]
S += B(["202 automated tests, all passing: 16 database/logic, 20 analytics, 7 UI, 93 edge cases, 66 CSV export.",
        "Tested: overselling is rejected and nothing is logged; invalid quantities rejected; duplicate SKU rejected; "
        "deleting a supplier keeps its products; passwords verify correctly and wrong ones fail; empty data and bad "
        "filters are handled; exports handle empty results.",
        "Add a screenshot of <font face='Courier'>pytest</font> output."])
S += [P("Challenges and learnings (use these honestly in the report)", h2)]
S += B(["Working in parallel before the backend was finished: we agreed function names early, and the UI used "
        "stand-in calculations until analytics was ready.",
        "Keeping stock correct: solved with atomic transactions and database constraints.",
        "Merge discipline: branches and pull requests so one person's push does not break another's work."])
S += [P("Industry relevance (for the report and slides)", h2),
      P("Retail, grocery, pharmacy, e-commerce and warehouse businesses all need inventory control. StockSense "
        "addresses stockouts and dead stock. To scale: PostgreSQL instead of SQLite, a REST API, integration with "
        "billing/POS and barcode scanners, cloud deployment, and later demand forecasting."),
      P("Questions Person 4 may get", h2),
      qa([("How did you test it?", "Automated pytest tests (202) on the backend, analytics, UI and CSV export, with an "
                                   "isolated temporary database per test so tests never touch real data."),
          ("What is CSV formula injection and how do you stop it?", "A cell starting with = + - or @ can run as a "
                                                                    "formula when opened in Excel. We put a tab in "
                                                                    "front of such cells so they are read as plain "
                                                                    "text."),
          ("Why does the CSV file start with a BOM?", "A hidden marker (UTF-8 BOM) so Excel shows the rupee symbol "
                                                      "and other characters correctly."),
          ("What industry uses this?", "Retail, grocery, pharmacy, e-commerce, warehouses and logistics."),
          ("What were the biggest challenges?", "Parallel work with 4 people and keeping stock consistent."),
          ("What is the future scope?", "Forecasting, barcode scanning, multi-store, supplier auto-ordering, "
                                        "cloud deployment."),
          ("Where does the sample data come from?", "We generated it ourselves with scripts: 30 products from 5 "
                                                    "suppliers, plus sales history with fast, slow and dead "
                                                    "products so every report is meaningful.")]),
      PB]

# ---------------------------------------------------------------- 6 skit
S += [P("6. Presentation skit (about 12 to 13 minutes)", h1),
      P("Speak naturally; do not read word for word. Keep the order and the hand-offs. The demo is done live by "
        "Person 3, with Person 1 and Person 4 standing by to answer. <b>Rehearse twice</b> and record a backup video "
        "of the demo in case the laptop or wifi fails."),
      table([["Time", "Speaker", "Topic"],
             ["0:00 - 2:30", "Person 1", "Problem, solution, architecture, database"],
             ["2:30 - 5:30", "Person 2", "Algorithms and data structures"],
             ["5:30 - 9:30", "Person 3", "Live demo and user flow"],
             ["9:30 - 12:30", "Person 4", "Testing, CSV export, industry relevance, conclusion"],
             ["After", "All", "Q&amp;A (anyone may answer; use section 7)"]], [3, 3, 11]),

      P("Person 1 (0:00 - 2:30)", h2),
      P("<b>P1:</b> \"Good morning. We are Group 3G, and our project is <b>StockSense</b>, a smart inventory "
        "management system built entirely in Python.\"", say),
      P("<b>P1:</b> \"Imagine a grocery shop that tracks stock in a notebook. Rice runs out on a busy weekend and "
        "sales are lost, while a shelf of unsold items ties up money. The owner cannot see what to reorder or what "
        "actually earns profit. Enterprise tools are too expensive for them. StockSense solves this: it records every "
        "sale and purchase, keeps stock correct automatically, warns when to reorder, and shows what sells and what "
        "does not.\"", say),
      P("<b>P1:</b> \"The system has three layers. A Streamlit interface, which Person 3 will show you; a Python "
        "backend with the logic; and an SQLite database. The interface never touches the database directly, which "
        "let the four of us build in parallel.\"", say),
      P("<b>P1:</b> \"My part was the foundation. Four tables: users, suppliers, products and transactions. Stock "
        "can only change through a sale or a purchase, and each one is saved as a single atomic step, so stock can "
        "never go negative and every unit is traceable. Passwords are stored as salted hashes, never plain text, "
        "and products are found by SKU through a hash map in constant time. Now Person 2 will explain how the "
        "system turns this data into decisions.\"", say),

      P("Person 2 (2:30 - 5:30)", h2),
      P("<b>P2:</b> \"Thank you. Storing data is not enough; the owner needs answers. We do this with simple, "
        "explainable algorithms, no machine learning.\"", say),
      P("<b>P2:</b> \"First, <b>reorder point</b>: average daily sales times supplier lead time, plus safety stock, "
        "rounded up. For rice: 15 a day, 3 days, safety 20 gives 65. When stock falls below 65, we alert and suggest "
        "how much to order. The urgent items come out of a <b>priority queue</b>, a heap, so the biggest shortage "
        "is always first.\"", say),
      P("<b>P2:</b> \"Second, <b>ABC analysis</b>. We sort products by revenue and track the cumulative percentage. "
        "The products that make the first 80% are class A, the next 15% class B, the rest class C. It tells the owner "
        "where to focus.\"", say),
      P("<b>P2:</b> \"Third, <b>dead stock</b>: products with stock but no sale in 30 days, ranked by how much "
        "money is stuck. And fourth, a <b>7-day moving average</b> that smooths daily noise so the trend is clear, "
        "counting quiet days as zero. These use sorting, hash maps, a heap and a sliding window. Person 3 will now "
        "show all of this live.\"", say),

      P("Person 3 (5:30 - 9:30)", h2),
      P("<b>P3:</b> \"I built the interface in Streamlit, so the whole project stays in Python. Let me log in as "
        "admin.\" <i>[Log in.]</i>", say),
      P("<b>P3:</b> \"The dashboard shows total products, stock value and today's sales, and the <b>Reorder "
        "Now</b> list, already sorted by urgency.\" <i>[Point to the list.]</i>", say),
      P("<b>P3:</b> \"Products page: search and filters, and as admin I can add, edit or delete. Staff accounts do "
        "not see these controls. There is also an Export CSV button.\" <i>[Add one product, click Export.]</i>", say),
      P("<b>P3:</b> \"Now a sale. I pick a product, enter quantity 3, submit. Stock drops immediately. If I try to "
        "sell more than we have...\" <i>[Try 9999.]</i> \"...the system refuses and nothing is saved.\"", say),
      P("<b>P3:</b> \"Back on the dashboard the numbers and alerts have updated. In Analytics there are three "
        "tabs: the sales trend with the moving average, the ABC split as a pie and bar chart, and the dead stock table "
        "showing money tied up.\" <i>[Click through the tabs.]</i>", say),
      P("<b>P3:</b> \"One design note: the interface contains no SQL. It only calls backend functions. Person 4 will "
        "now tell you how we know it works.\"", say),

      P("Person 4 (9:30 - 12:30)", h2),
      P("<b>P4:</b> \"To test it, we wrote 202 automated tests, and all pass. They check that overselling is "
        "rejected, invalid quantities and duplicate SKUs are refused, deleting a supplier keeps its products, "
        "passwords verify correctly, exports handle empty data, and the UI contains no SQL. Each test runs on a fresh "
        "temporary database.\" <i>[Show the pytest result slide.]</i>", say),
      P("<b>P4:</b> \"We also generated sample data, 30 grocery products from 5 suppliers with sales history, so the "
        "analytics are meaningful. And owners can export inventory and sales to CSV, with protection against "
        "spreadsheet formula injection.\" <i>[Only say 'with sales history' once that data exists.]</i>", say),
      P("<b>P4:</b> \"Industry use: any retailer, grocery chain, pharmacy, e-commerce seller or warehouse has this "
        "problem. To scale, we would move SQLite to PostgreSQL, add a REST API, connect billing and barcode "
        "scanners, and deploy to the cloud.\"", say),
      P("<b>P4:</b> \"Our biggest challenges were building in parallel as four people, which we solved with agreed "
        "function names, branches and pull requests, and keeping stock consistent, which we solved with atomic "
        "transactions. Future scope: demand forecasting, multi-store support and automatic supplier orders. Thank you. "
        "We are happy to take questions.\"", say),
      PB]

# ---------------------------------------------------------------- 7 rapid fire
S += [P("7. Rapid-fire questions anyone might get", h1),
      P("Practise answering these <b>out of your own area</b>. If you do not know, say what you do know and name "
        "the teammate who built it, but try to answer first."),
      table([["Question", "Short answer"],
             ["What does StockSense do?", "Tracks stock, warns when to reorder, shows best sellers and dead stock."],
             ["Why Python?", "Fast to build, great libraries (pandas, Plotly, Streamlit), widely used in industry."],
             ["Why SQLite?", "No server, built in, enough for a prototype; PostgreSQL for production."],
             ["Which data structures did you use?", "Hash map (SKU index, totals), heap/priority queue (reorder list), "
                                                    "sorted list (ABC), sliding window (moving average)."],
             ["Reorder point formula?", "Average daily sales x lead time + safety stock, rounded up."],
             ["When does the reorder alert fire?", "When stock is below the reorder point."],
             ["What is ABC analysis?", "Rank by revenue: A = first 80%, B = next 15%, C = last 5%."],
             ["What is dead stock?", "Stock on the shelf with no sale in the last N days."],
             ["How do you stop negative stock?", "Guarded update in code plus a CHECK constraint in the database."],
             ["How are passwords protected?", "Salted PBKDF2-SHA256 hashes."],
             ["What is the UI-backend separation?", "UI calls functions only; no SQL in UI; easy to change either side."],
             ["Is there machine learning?", "No. Rule-based logic and averages; explainable and needs no training data."],
             ["How did you test?", "202 pytest tests with an isolated temp database; plus manual demo runs."],
             ["What is CSV formula injection?", "A cell starting with = could run as a formula in Excel; we prefix a "
                                                "tab so it stays text."],
             ["How did four people work together?", "One GitHub repo, branches and pull requests, agreed function "
                                                    "signatures from day 1."],
             ["How would it scale?", "PostgreSQL, REST API, cloud deploy, POS and barcode integration."],
             ["What would you improve?", "Forecasting, multi-store, supplier auto-orders, password reset."],
             ["What was your own contribution?", "Say your files and 2 decisions you made and why (sections 2 to 5)."]],
            [6, 11]),
      PB]

# ---------------------------------------------------------------- 8 checklist
S += [P("8. Last checklist", h1),
      table([["Owner", "Task", "Done?"],
             ["Person 4", "Add sales history (about 60 days, with fast, slow and never-sold products) to the sample "
                          "data", "[ ]"],
             ["Person 4", "Add python-pptx to requirements.txt; run docs/build_presentation.py; check the slides and "
                          "the report (10 pages or fewer); commit them", "[ ]"],
             ["Person 4", "Set <font face='Courier'>git config user.name</font> and <font face='Courier'>user.email"
                          "</font> (commits currently show 'Your Name')", "[ ]"],
             ["Person 3", "Delete the unused stand-in analytics code in pages/_utils.py; click through every page "
                          "once", "[ ]"],
             ["Person 2", "Be ready to explain the suggested-order rule and why the alert is strictly below the reorder "
                          "point", "[ ]"],
             ["Person 1", "Review and merge pull requests; run pytest on main; run <font face='Courier'>streamlit "
                          "run app.py</font> and click through every page", "[ ]"],
             ["Everyone", "Read sections 2 to 5 of this guide; practise section 7 questions on each other", "[ ]"],
             ["Everyone", "Rehearse the skit twice with a timer (target 12 minutes)", "[ ]"],
             ["Everyone", "Record a backup screen video of the demo; test laptop, charger, display adapter", "[ ]"],
             ["Everyone", "Confirm your presentation slot time (the guideline says presentations began 5 Nov); "
                          "all members must be present", "[ ]"]], [2.4, 13.2, 1.4]),
      SP(10),
      P("Marks reminder: Technical 25, Report 25, Presentation and demo with industry relevance 25, Soft skills "
        "25 (clarity, teamwork, handling questions calmly, time, conduct). Total 100, scaled to 50.")]


# ====================================================================== PDF RENDERER
def build_pdf():
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    navy = colors.HexColor("#" + NAVY_HEX)
    base = ParagraphStyle("b", parent=ss["Normal"], fontSize=10.5, leading=14.5, spaceAfter=3)
    cell = ParagraphStyle("c", parent=base, fontSize=9, leading=11.5, spaceAfter=0)
    styles = {
        "title": ParagraphStyle("t", parent=ss["Title"], fontSize=26, spaceAfter=4),
        "sub": ParagraphStyle("s", parent=base, fontSize=12, textColor=colors.grey, alignment=1, spaceAfter=14),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=18, textColor=navy, spaceBefore=2, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, textColor=navy, spaceBefore=10,
                             spaceAfter=3, keepWithNext=1),
        "body": base,
        "code": ParagraphStyle("code", parent=base, fontName="Courier", fontSize=9.5, leading=12.5,
                               backColor=colors.HexColor("#f2f6fa"), borderPadding=5, spaceBefore=3,
                               spaceAfter=8, leftIndent=6),
        "say": ParagraphStyle("say", parent=base, leftIndent=10, spaceAfter=5),
        "bul": ParagraphStyle("bl", parent=base, leftIndent=14, bulletIndent=2, spaceAfter=2),
    }
    cellb = ParagraphStyle("cb", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")

    flow = []
    for blk in S:
        kind = blk[0]
        if kind == "p":
            flow.append(Paragraph(blk[1], styles[blk[2]]))
        elif kind == "bul":
            flow.append(Paragraph(blk[1], styles["bul"], bulletText="•"))
        elif kind == "space":
            flow.append(Spacer(1, blk[1]))
        elif kind == "pb":
            flow.append(PageBreak())
        elif kind == "table":
            rows, widths = blk[1], blk[2]
            data = [[Paragraph(str(c), cellb if r == 0 else cell) for c in row] for r, row in enumerate(rows)]
            t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
            t.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")])]))
            flow.append(t)
        elif kind == "note":
            t = Table([[Paragraph(blk[1], cell)]], colWidths=[17 * cm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(blk[2])),
                                   ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0c36a")),
                                   ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            flow.append(t)

    def footer(c, d):
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(2 * cm, 1 * cm, "StockSense Team Guide")
        c.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Page {d.page}")

    doc = SimpleDocTemplate(PDF_OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                            bottomMargin=1.8 * cm, title="StockSense Team Guide", author="StockSense Team")
    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    print("wrote", PDF_OUT)


# ====================================================================== DOCX RENDERER
class _Runs(HTMLParser):
    """Turns the small inline markup into (text, bold, italic, mono) runs; '\\n' means a line break."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.runs, self.b, self.i, self.m, self.stack = [], 0, 0, 0, []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.runs.append(("\n", 0, 0, 0))
        elif tag == "b":
            self.b += 1; self.stack.append("b")
        elif tag == "i":
            self.i += 1; self.stack.append("i")
        elif tag == "font":
            mono = "courier" in dict(attrs).get("face", "").lower()
            self.m += mono; self.stack.append("m" if mono else "x")

    def handle_endtag(self, tag):
        if tag in ("b", "i", "font") and self.stack:
            t = self.stack.pop()
            if t == "b": self.b -= 1
            elif t == "i": self.i -= 1
            elif t == "m": self.m -= 1

    def handle_data(self, data):
        self.runs.append((data, self.b, self.i, self.m))


def _runs(markup):
    p = _Runs()
    p.feed(markup)
    return p.runs


def build_docx():
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Calibri", Pt(10.5)
    for name, size in (("Heading 1", 18), ("Heading 2", 12.5), ("Title", 26)):
        st = doc.styles[name]
        st.font.name, st.font.size = "Calibri", Pt(size)
        st.font.color.rgb = RGBColor.from_string(NAVY_HEX)
    sec.footer.paragraphs[0].text = "StockSense Team Guide"

    def shade(cell_or_par, hex_fill):
        el = cell_or_par._tc.get_or_add_tcPr() if hasattr(cell_or_par, "_tc") else cell_or_par._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
        el.append(shd)

    def fill(par, markup, size=None, color=None, force_bold=False, mono_all=False):
        for text, b, i, m in _runs(markup):
            if text == "\n":
                par.add_run().add_break()
                continue
            r = par.add_run(text)
            r.bold = bool(b) or force_bold
            r.italic = bool(i)
            if m or mono_all:
                r.font.name = "Courier New"
            if size:
                r.font.size = Pt(size)
            if color:
                r.font.color.rgb = RGBColor.from_string(color)

    for blk in S:
        kind = blk[0]
        if kind == "p":
            text, st = blk[1], blk[2]
            if st == "title":
                par = doc.add_paragraph(style="Title"); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                fill(par, text)
            elif st == "sub":
                par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                fill(par, text, size=12, color="808080")
            elif st in ("h1", "h2"):
                par = doc.add_heading(level=1 if st == "h1" else 2)
                fill(par, text)
            elif st == "code":
                par = doc.add_paragraph(); shade(par, "F2F6FA"); fill(par, text, size=9.5, mono_all=True)
            elif st == "say":
                par = doc.add_paragraph(); par.paragraph_format.left_indent = Cm(0.8); fill(par, text)
            else:
                fill(doc.add_paragraph(), text)
        elif kind == "bul":
            fill(doc.add_paragraph(style="List Bullet"), blk[1])
        elif kind == "space":
            if blk[1] >= 20:
                doc.add_paragraph()
        elif kind == "pb":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif kind == "table":
            rows, widths = blk[1], blk[2]
            t = doc.add_table(rows=len(rows), cols=len(widths))
            t.style = "Table Grid"; t.autofit = False; t.alignment = WD_TABLE_ALIGNMENT.CENTER
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    cell = t.cell(r, c); cell.width = Cm(widths[c])
                    par = cell.paragraphs[0]
                    if r == 0:
                        shade(cell, NAVY_HEX)
                        fill(par, str(val), size=9, color="FFFFFF", force_bold=True)
                    else:
                        if r % 2 == 0:
                            shade(cell, "F2F6FA")
                        fill(par, str(val), size=9)
            doc.add_paragraph()
        elif kind == "note":
            t = doc.add_table(rows=1, cols=1); t.style = "Table Grid"; t.autofit = False
            cell = t.cell(0, 0); cell.width = Cm(17)
            shade(cell, blk[2].lstrip("#").upper())
            fill(cell.paragraphs[0], blk[1], size=9)
            doc.add_paragraph()

    doc.core_properties.title = "StockSense Team Guide"
    doc.core_properties.author = "StockSense Team"
    doc.save(DOCX_OUT)
    print("wrote", DOCX_OUT)


if __name__ == "__main__":
    build_pdf()
    build_docx()
