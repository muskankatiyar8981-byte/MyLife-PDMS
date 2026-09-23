from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mylife-secret-key-2026"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


# =========================================================
# CREATE DATABASE TABLES
# =========================================================

def init_db():

    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            task_date TEXT,
            task_time TEXT,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            study_date TEXT NOT NULL,
            study_time TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            due_date TEXT NOT NULL,
            due_time TEXT,
            priority TEXT NOT NULL DEFAULT 'Medium',
            completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            budget REAL NOT NULL DEFAULT 0,
            low_limit REAL NOT NULL DEFAULT 100
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            price REAL NOT NULL DEFAULT 0,
            priority TEXT NOT NULL DEFAULT 'Medium',
            shopping_date TEXT NOT NULL,
            purchased INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# =========================================================
# SIGNUP
# =========================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:

            return render_template(
                "signup.html",
                error="Please fill all fields."
            )

        db = get_db()

        existing = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing:

            db.close()

            return render_template(
                "signup.html",
                error="Email already registered."
            )

        hashed_password = generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )

        db.execute("""
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
        """, (
            name,
            email,
            hashed_password
        ))

        db.commit()
        db.close()

        return redirect(url_for("login"))

    return render_template("signup.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        db = get_db()

        user = db.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()

        db.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid email or password."
        )

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = date.today().isoformat()

    db = get_db()

    # -----------------------------------------
    # TODAY'S TASKS
    # -----------------------------------------

    tasks_today = db.execute("""
        SELECT COUNT(*) AS count
        FROM tasks
        WHERE user_id = ?
        AND task_date = ?
    """, (
        user_id,
        today
    )).fetchone()["count"]

    # -----------------------------------------
    # TODAY'S STUDY PLANS
    # -----------------------------------------

    study_today = db.execute("""
        SELECT COUNT(*) AS count
        FROM study_plans
        WHERE user_id = ?
        AND study_date = ?
    """, (
        user_id,
        today
    )).fetchone()["count"]

    # -----------------------------------------
    # TODAY'S EXPENSE
    # -----------------------------------------

    today_expense = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = ?
        AND expense_date = ?
    """, (
        user_id,
        today
    )).fetchone()["total"]

    # =====================================================
    # OVERALL PROGRESS
    # =====================================================

    # TODO

    total_tasks = db.execute("""
        SELECT COUNT(*) AS total
        FROM tasks
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    completed_tasks = db.execute("""
        SELECT COUNT(*) AS total
        FROM tasks
        WHERE user_id = ?
        AND completed = 1
    """, (
        user_id,
    )).fetchone()["total"]

    # STUDY

    total_study = db.execute("""
        SELECT COUNT(*) AS total
        FROM study_plans
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    completed_study = db.execute("""
        SELECT COUNT(*) AS total
        FROM study_plans
        WHERE user_id = ?
        AND completed = 1
    """, (
        user_id,
    )).fetchone()["total"]

    # ASSIGNMENTS

    total_assignments = db.execute("""
        SELECT COUNT(*) AS total
        FROM assignments
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    completed_assignments = db.execute("""
        SELECT COUNT(*) AS total
        FROM assignments
        WHERE user_id = ?
        AND completed = 1
    """, (
        user_id,
    )).fetchone()["total"]

    # -----------------------------------------
    # COMBINED PROGRESS
    # -----------------------------------------

    total_items = (
        total_tasks
        + total_study
        + total_assignments
    )

    completed_items = (
        completed_tasks
        + completed_study
        + completed_assignments
    )

    if total_items > 0:

        progress = round(
            (completed_items / total_items) * 100
        )

    else:

        progress = 0

    db.close()

    return render_template(
        "dashboard.html",
        tasks_today=tasks_today,
        study_today=study_today,
        today_expense=today_expense,
        progress=progress
    )


# =========================================================
# TODO PAGE
# =========================================================

@app.route("/todo")
def todo():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    tasks = db.execute("""
        SELECT *
        FROM tasks
        WHERE user_id = ?
        ORDER BY task_date ASC, task_time ASC
    """, (
        session["user_id"],
    )).fetchall()

    db.close()

    return render_template(
        "todo.html",
        tasks=tasks
    )


# =========================================================
# ADD TODO
# =========================================================

@app.route("/add-task", methods=["POST"])
def add_task():

    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    task_date = request.form.get(
        "task_date",
        ""
    )

    task_time = request.form.get(
        "task_time",
        ""
    )

    if title:

        db = get_db()

        db.execute("""
            INSERT INTO tasks
            (user_id, title, task_date, task_time)
            VALUES (?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            task_date,
            task_time
        ))

        db.commit()
        db.close()

    return redirect(url_for("todo"))


# =========================================================
# TOGGLE TODO
# GET + POST BOTH ALLOWED
# =========================================================

@app.route(
    "/toggle-task/<int:task_id>",
    methods=["GET", "POST"]
)
def toggle_task(task_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        UPDATE tasks
        SET completed =
            CASE
                WHEN completed = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
        AND user_id = ?
    """, (
        task_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("todo"))


# =========================================================
# DELETE TODO
# =========================================================

@app.route(
    "/delete-task/<int:task_id>",
    methods=["GET", "POST"]
)
def delete_task(task_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        DELETE FROM tasks
        WHERE id = ?
        AND user_id = ?
    """, (
        task_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("todo"))


# =========================================================
# STUDY PAGE
# =========================================================

@app.route("/study")
def study():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    plans = db.execute("""
        SELECT *
        FROM study_plans
        WHERE user_id = ?
        ORDER BY study_date ASC, study_time ASC
    """, (
        session["user_id"],
    )).fetchall()

    db.close()

    return render_template(
        "study.html",
        plans=plans
    )


# =========================================================
# ADD STUDY
# =========================================================

@app.route("/add-study", methods=["POST"])
def add_study():

    if "user_id" not in session:
        return redirect(url_for("login"))

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    topic = request.form.get(
        "topic",
        ""
    ).strip()

    study_date = request.form.get(
        "study_date",
        ""
    )

    study_time = request.form.get(
        "study_time",
        ""
    )

    if subject and topic and study_date and study_time:

        db = get_db()

        db.execute("""
            INSERT INTO study_plans
            (
                user_id,
                subject,
                topic,
                study_date,
                study_time
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            subject,
            topic,
            study_date,
            study_time
        ))

        db.commit()
        db.close()

    return redirect(url_for("study"))


# =========================================================
# TOGGLE STUDY
# GET + POST BOTH ALLOWED
# =========================================================

@app.route(
    "/toggle-study/<int:plan_id>",
    methods=["GET", "POST"]
)
def toggle_study(plan_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        UPDATE study_plans
        SET completed =
            CASE
                WHEN completed = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
        AND user_id = ?
    """, (
        plan_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("study"))


# =========================================================
# DELETE STUDY
# =========================================================

@app.route(
    "/delete-study/<int:plan_id>",
    methods=["GET", "POST"]
)
def delete_study(plan_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        DELETE FROM study_plans
        WHERE id = ?
        AND user_id = ?
    """, (
        plan_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("study"))


# =========================================================
# ASSIGNMENTS PAGE
# =========================================================

@app.route("/assignments")
def assignments():

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    assignments_list = db.execute("""
        SELECT *
        FROM assignments
        WHERE user_id = ?
        ORDER BY due_date ASC, due_time ASC
    """, (
        session["user_id"],
    )).fetchall()

    db.close()

    return render_template(
        "assignments.html",
        assignments=assignments_list
    )


# =========================================================
# ADD ASSIGNMENT
# =========================================================

@app.route("/add-assignment", methods=["POST"])
def add_assignment():

    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    subject = request.form.get(
        "subject",
        ""
    ).strip()

    due_date = request.form.get(
        "due_date",
        ""
    )

    due_time = request.form.get(
        "due_time",
        ""
    )

    priority = request.form.get(
        "priority",
        "Medium"
    )

    if title and subject and due_date:

        db = get_db()

        db.execute("""
            INSERT INTO assignments
            (
                user_id,
                title,
                subject,
                due_date,
                due_time,
                priority
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            subject,
            due_date,
            due_time,
            priority
        ))

        db.commit()
        db.close()

    return redirect(url_for("assignments"))


# =========================================================
# TOGGLE ASSIGNMENT
# GET + POST BOTH ALLOWED
# =========================================================

@app.route(
    "/toggle-assignment/<int:assignment_id>",
    methods=["GET", "POST"]
)
def toggle_assignment(assignment_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        UPDATE assignments
        SET completed =
            CASE
                WHEN completed = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
        AND user_id = ?
    """, (
        assignment_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("assignments"))


# =========================================================
# DELETE ASSIGNMENT
# =========================================================

@app.route(
    "/delete-assignment/<int:assignment_id>",
    methods=["GET", "POST"]
)
def delete_assignment(assignment_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        DELETE FROM assignments
        WHERE id = ?
        AND user_id = ?
    """, (
        assignment_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("assignments"))


# =========================================================
# EXPENSE PAGE
# =========================================================

@app.route("/expenses")
def expenses():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db()

    expense_list = db.execute("""
        SELECT *
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC, id DESC
    """, (
        user_id,
    )).fetchall()

    total_expense = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    today = date.today().isoformat()

    today_expense = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = ?
        AND expense_date = ?
    """, (
        user_id,
        today
    )).fetchone()["total"]

    budget_row = db.execute("""
        SELECT *
        FROM budgets
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()

    if budget_row:

        budget = budget_row["budget"]
        low_limit = budget_row["low_limit"]

    else:

        budget = 0
        low_limit = 100

    remaining = budget - total_expense

    db.close()

    return render_template(
        "expense.html",
        expenses=expense_list,
        total_expense=total_expense,
        today_expense=today_expense,
        budget=budget,
        low_limit=low_limit,
        remaining=remaining
    )


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route("/add-expense", methods=["POST"])
def add_expense():

    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    category = request.form.get(
        "category",
        "Other"
    )

    amount = request.form.get(
        "amount",
        "0"
    )

    expense_date = request.form.get(
        "expense_date",
        ""
    )

    if title and expense_date:

        try:
            amount = float(amount)
        except ValueError:
            amount = 0

        db = get_db()

        db.execute("""
            INSERT INTO expenses
            (
                user_id,
                title,
                category,
                amount,
                expense_date
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            title,
            category,
            amount,
            expense_date
        ))

        db.commit()
        db.close()

    return redirect(url_for("expenses"))


# =========================================================
# EDIT EXPENSE
# =========================================================

@app.route("/edit-expense/<int:expense_id>")
def edit_expense(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    expense = db.execute("""
        SELECT *
        FROM expenses
        WHERE id = ?
        AND user_id = ?
    """, (
        expense_id,
        session["user_id"]
    )).fetchone()

    db.close()

    if not expense:
        return redirect(url_for("expenses"))

    return render_template(
        "expense.html",
        edit_expense=expense
    )


# =========================================================
# UPDATE EXPENSE
# =========================================================

@app.route(
    "/update-expense/<int:expense_id>",
    methods=["POST"]
)
def update_expense(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    category = request.form.get(
        "category",
        "Other"
    )

    amount = request.form.get(
        "amount",
        "0"
    )

    expense_date = request.form.get(
        "expense_date",
        ""
    )

    try:
        amount = float(amount)
    except ValueError:
        amount = 0

    db = get_db()

    db.execute("""
        UPDATE expenses
        SET title = ?,
            category = ?,
            amount = ?,
            expense_date = ?
        WHERE id = ?
        AND user_id = ?
    """, (
        title,
        category,
        amount,
        expense_date,
        expense_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("expenses"))


# =========================================================
# DELETE EXPENSE
# =========================================================

@app.route(
    "/delete-expense/<int:expense_id>",
    methods=["GET", "POST"]
)
def delete_expense(expense_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        DELETE FROM expenses
        WHERE id = ?
        AND user_id = ?
    """, (
        expense_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("expenses"))


# =========================================================
# SET BUDGET
# =========================================================

@app.route("/set-budget", methods=["POST"])
def set_budget():

    if "user_id" not in session:
        return redirect(url_for("login"))

    try:
        budget = float(
            request.form.get(
                "budget",
                0
            )
        )
    except ValueError:
        budget = 0

    try:
        low_limit = float(
            request.form.get(
                "low_limit",
                100
            )
        )
    except ValueError:
        low_limit = 100

    db = get_db()

    existing = db.execute("""
        SELECT id
        FROM budgets
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if existing:

        db.execute("""
            UPDATE budgets
            SET budget = ?,
                low_limit = ?
            WHERE user_id = ?
        """, (
            budget,
            low_limit,
            session["user_id"]
        ))

    else:

        db.execute("""
            INSERT INTO budgets
            (
                user_id,
                budget,
                low_limit
            )
            VALUES (?, ?, ?)
        """, (
            session["user_id"],
            budget,
            low_limit
        ))

    db.commit()
    db.close()

    return redirect(url_for("expenses"))


# =========================================================
# SHOPPING PAGE
# =========================================================

@app.route("/shopping")
def shopping():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db()

    items = db.execute("""
        SELECT *
        FROM shopping_items
        WHERE user_id = ?
        ORDER BY shopping_date ASC, priority DESC
    """, (
        user_id,
    )).fetchall()

    total_items = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM shopping_items
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    pending_items = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM shopping_items
        WHERE user_id = ?
        AND purchased = 0
    """, (
        user_id,
    )).fetchone()["total"]

    purchased_items = db.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM shopping_items
        WHERE user_id = ?
        AND purchased = 1
    """, (
        user_id,
    )).fetchone()["total"]

    estimated_cost = db.execute("""
        SELECT COALESCE(
            SUM(quantity * price),
            0
        ) AS total
        FROM shopping_items
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    db.close()

    return render_template(
        "shopping.html",
        items=items,
        total_items=total_items,
        pending_items=pending_items,
        purchased_items=purchased_items,
        estimated_cost=estimated_cost
    )


# =========================================================
# ADD SHOPPING
# =========================================================

@app.route("/add-shopping", methods=["POST"])
def add_shopping():

    if "user_id" not in session:
        return redirect(url_for("login"))

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        "Other"
    )

    try:
        quantity = int(
            request.form.get(
                "quantity",
                1
            )
        )
    except ValueError:
        quantity = 1

    try:
        price = float(
            request.form.get(
                "price",
                0
            )
        )
    except ValueError:
        price = 0

    priority = request.form.get(
        "priority",
        "Medium"
    )

    shopping_date = request.form.get(
        "shopping_date",
        ""
    )

    if item_name and shopping_date:

        db = get_db()

        db.execute("""
            INSERT INTO shopping_items
            (
                user_id,
                item_name,
                category,
                quantity,
                price,
                priority,
                shopping_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            item_name,
            category,
            quantity,
            price,
            priority,
            shopping_date
        ))

        db.commit()
        db.close()

    return redirect(url_for("shopping"))


# =========================================================
# EDIT SHOPPING
# =========================================================

@app.route("/edit-shopping/<int:item_id>")
def edit_shopping(item_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    item = db.execute("""
        SELECT *
        FROM shopping_items
        WHERE id = ?
        AND user_id = ?
    """, (
        item_id,
        session["user_id"]
    )).fetchone()

    db.close()

    if not item:
        return redirect(url_for("shopping"))

    return render_template(
        "shopping.html",
        edit_item=item
    )


# =========================================================
# UPDATE SHOPPING
# =========================================================

@app.route(
    "/update-shopping/<int:item_id>",
    methods=["POST"]
)
def update_shopping(item_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    item_name = request.form.get(
        "item_name",
        ""
    ).strip()

    category = request.form.get(
        "category",
        "Other"
    )

    try:
        quantity = int(
            request.form.get(
                "quantity",
                1
            )
        )
    except ValueError:
        quantity = 1

    try:
        price = float(
            request.form.get(
                "price",
                0
            )
        )
    except ValueError:
        price = 0

    priority = request.form.get(
        "priority",
        "Medium"
    )

    shopping_date = request.form.get(
        "shopping_date",
        ""
    )

    db = get_db()

    db.execute("""
        UPDATE shopping_items
        SET item_name = ?,
            category = ?,
            quantity = ?,
            price = ?,
            priority = ?,
            shopping_date = ?
        WHERE id = ?
        AND user_id = ?
    """, (
        item_name,
        category,
        quantity,
        price,
        priority,
        shopping_date,
        item_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("shopping"))


# =========================================================
# TOGGLE SHOPPING
# =========================================================

@app.route(
    "/toggle-shopping/<int:item_id>",
    methods=["GET", "POST"]
)
def toggle_shopping(item_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        UPDATE shopping_items
        SET purchased =
            CASE
                WHEN purchased = 1 THEN 0
                ELSE 1
            END
        WHERE id = ?
        AND user_id = ?
    """, (
        item_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("shopping"))


# =========================================================
# DELETE SHOPPING
# =========================================================

@app.route(
    "/delete-shopping/<int:item_id>",
    methods=["GET", "POST"]
)
def delete_shopping(item_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()

    db.execute("""
        DELETE FROM shopping_items
        WHERE id = ?
        AND user_id = ?
    """, (
        item_id,
        session["user_id"]
    ))

    db.commit()
    db.close()

    return redirect(url_for("shopping"))


# =========================================================
# CALENDAR
# =========================================================

@app.route("/calendar")
def calendar():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db()

    tasks = db.execute("""
        SELECT
            id,
            title,
            task_date,
            task_time,
            completed
        FROM tasks
        WHERE user_id = ?
        AND task_date IS NOT NULL
        AND task_date != ''
        ORDER BY task_date, task_time
    """, (
        user_id,
    )).fetchall()

    study_plans = db.execute("""
        SELECT
            id,
            subject,
            topic,
            study_date,
            study_time,
            completed
        FROM study_plans
        WHERE user_id = ?
        AND study_date IS NOT NULL
        AND study_date != ''
        ORDER BY study_date, study_time
    """, (
        user_id,
    )).fetchall()

    assignments_list = db.execute("""
        SELECT
            id,
            title,
            subject,
            due_date,
            due_time,
            priority,
            completed
        FROM assignments
        WHERE user_id = ?
        AND due_date IS NOT NULL
        AND due_date != ''
        ORDER BY due_date, due_time
    """, (
        user_id,
    )).fetchall()

    expense_list = db.execute("""
        SELECT
            id,
            title,
            category,
            amount,
            expense_date
        FROM expenses
        WHERE user_id = ?
        AND expense_date IS NOT NULL
        AND expense_date != ''
        ORDER BY expense_date
    """, (
        user_id,
    )).fetchall()

    shopping_items = db.execute("""
        SELECT
            id,
            item_name,
            category,
            quantity,
            price,
            priority,
            shopping_date,
            purchased
        FROM shopping_items
        WHERE user_id = ?
        AND shopping_date IS NOT NULL
        AND shopping_date != ''
        ORDER BY shopping_date
    """, (
        user_id,
    )).fetchall()

    db.close()

    tasks = [dict(row) for row in tasks]
    study_plans = [dict(row) for row in study_plans]
    assignments_list = [dict(row) for row in assignments_list]
    expense_list = [dict(row) for row in expense_list]
    shopping_items = [dict(row) for row in shopping_items]

    return render_template(
        "calendar.html",
        tasks=tasks,
        study_plans=study_plans,
        assignments=assignments_list,
        expenses=expense_list,
        shopping_items=shopping_items
    )


# =========================================================
# SUMMARY
# =========================================================

@app.route("/summary")
def summary():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    db = get_db()

    tasks = db.execute("""
        SELECT *
        FROM tasks
        WHERE user_id = ?
        ORDER BY task_date ASC, task_time ASC
    """, (
        user_id,
    )).fetchall()

    study_plans = db.execute("""
        SELECT *
        FROM study_plans
        WHERE user_id = ?
        ORDER BY study_date ASC, study_time ASC
    """, (
        user_id,
    )).fetchall()

    assignments_list = db.execute("""
        SELECT *
        FROM assignments
        WHERE user_id = ?
        ORDER BY due_date ASC, due_time ASC
    """, (
        user_id,
    )).fetchall()

    expenses_list = db.execute("""
        SELECT *
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC
    """, (
        user_id,
    )).fetchall()

    shopping_items = db.execute("""
        SELECT *
        FROM shopping_items
        WHERE user_id = ?
        ORDER BY shopping_date ASC
    """, (
        user_id,
    )).fetchall()

    total_expense = db.execute("""
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    estimated_cost = db.execute("""
        SELECT COALESCE(
            SUM(quantity * price),
            0
        ) AS total
        FROM shopping_items
        WHERE user_id = ?
    """, (
        user_id,
    )).fetchone()["total"]

    task_count = len(tasks)
    study_count = len(study_plans)
    assignment_count = len(assignments_list)
    expense_count = len(expenses_list)
    shopping_count = len(shopping_items)

    db.close()

    return render_template(
        "summary.html",
        tasks=tasks,
        study_plans=study_plans,
        assignments=assignments_list,
        expenses=expenses_list,
        shopping_items=shopping_items,
        total_expense=total_expense,
        estimated_cost=estimated_cost,
        task_count=task_count,
        study_count=study_count,
        assignment_count=assignment_count,
        expense_count=expense_count,
        shopping_count=shopping_count
    )


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        port=5000
    )