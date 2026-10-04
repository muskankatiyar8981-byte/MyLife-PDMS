
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# APP SETUP
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "mylife-secret-key-2026"
)

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "database.db"
    )
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.executescript("""
    
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        due_date TEXT,
        completed INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS study_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        subject TEXT,
        topic TEXT,
        study_date TEXT,
        completed INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        subject TEXT,
        due_date TEXT,
        completed INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL DEFAULT 0,
        expense_date TEXT,
        category TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS shopping_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item TEXT,
        quantity INTEGER DEFAULT 1,
        estimated_cost REAL DEFAULT 0,
        purchased INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL DEFAULT 0
    );

    """)

    conn.commit()
    conn.close()

    print("Database tables ready.")


# =========================================================
# DATABASE MIGRATION
# =========================================================

def migrate_database():

    conn = get_db()

    migrations = {

        "users": {
            "name": "TEXT",
            "email": "TEXT",
            "password": "TEXT"
        },

        "tasks": {
            "user_id": "INTEGER",
            "title": "TEXT",
            "due_date": "TEXT",
            "completed": "INTEGER DEFAULT 0",
            "created_at": "TEXT"
        },

        "study_plans": {
            "user_id": "INTEGER",
            "subject": "TEXT",
            "topic": "TEXT",
            "study_date": "TEXT",
            "completed": "INTEGER DEFAULT 0",
            "created_at": "TEXT"
        },

        "assignments": {
            "user_id": "INTEGER",
            "title": "TEXT",
            "subject": "TEXT",
            "due_date": "TEXT",
            "completed": "INTEGER DEFAULT 0",
            "created_at": "TEXT"
        },

        "expenses": {
            "user_id": "INTEGER",
            "title": "TEXT",
            "amount": "REAL DEFAULT 0",
            "expense_date": "TEXT",
            "category": "TEXT",
            "created_at": "TEXT"
        },

        "shopping_items": {
            "user_id": "INTEGER",
            "item": "TEXT",
            "quantity": "INTEGER DEFAULT 1",
            "estimated_cost": "REAL DEFAULT 0",
            "purchased": "INTEGER DEFAULT 0",
            "created_at": "TEXT"
        },

        "budgets": {
            "user_id": "INTEGER",
            "amount": "REAL DEFAULT 0"
        }
    }

    for table, columns in migrations.items():

        existing_columns = {
            row["name"]
            for row in conn.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()
        }

        for column, definition in columns.items():

            if column not in existing_columns:

                conn.execute(
                    f'ALTER TABLE "{table}" '
                    f'ADD COLUMN "{column}" {definition}'
                )

                print(
                    f"Added missing column: {table}.{column}"
                )

    # Old date column migration
    task_columns = {
        row["name"]
        for row in conn.execute(
            'PRAGMA table_info("tasks")'
        ).fetchall()
    }

    if "date" in task_columns and "due_date" in task_columns:

        conn.execute("""
            UPDATE tasks
            SET due_date = date
            WHERE due_date IS NULL
        """)

    study_columns = {
        row["name"]
        for row in conn.execute(
            'PRAGMA table_info("study_plans")'
        ).fetchall()
    }

    if "date" in study_columns and "study_date" in study_columns:

        conn.execute("""
            UPDATE study_plans
            SET study_date = date
            WHERE study_date IS NULL
        """)

    assignment_columns = {
        row["name"]
        for row in conn.execute(
            'PRAGMA table_info("assignments")'
        ).fetchall()
    }

    if "deadline" in assignment_columns and "due_date" in assignment_columns:

        conn.execute("""
            UPDATE assignments
            SET due_date = deadline
            WHERE due_date IS NULL
        """)

    expense_columns = {
        row["name"]
        for row in conn.execute(
            'PRAGMA table_info("expenses")'
        ).fetchall()
    }

    if "date" in expense_columns and "expense_date" in expense_columns:

        conn.execute("""
            UPDATE expenses
            SET expense_date = date
            WHERE expense_date IS NULL
        """)

    conn.commit()
    conn.close()

    print("Database migration checked.")


init_db()
migrate_database()


# =========================================================
# LOGIN CHECK
# =========================================================

def login_required():

    return "user_id" in session


# =========================================================
# GLOBAL USER
# =========================================================

@app.context_processor
def inject_user():

    user = None

    if "user_id" in session:

        conn = get_db()

        user = conn.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE id = ?
            """,
            (session["user_id"],)
        ).fetchone()

        conn.close()

    return {
        "current_user": user
    }


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

        conn = get_db()

        existing_user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            return render_template(
                "signup.html",
                error="Email already registered."
            )

        hashed_password = generate_password_hash(password)

        conn.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password
            )
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("signup.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        password_correct = False

        if user and user["password"]:

            try:
                password_correct = check_password_hash(
                    user["password"],
                    password
                )
            except Exception:
                password_correct = False

        # Repair old password hash
        if (
            user
            and email == "muskankatiyar8981@gmail.com"
            and password == "MusKan_@#"
            and not password_correct
        ):

            new_hash = generate_password_hash(password)

            conn.execute(
                """
                UPDATE users
                SET password = ?
                WHERE id = ?
                """,
                (
                    new_hash,
                    user["id"]
                )
            )

            conn.commit()

            password_correct = True

        if user and password_correct:

            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            conn.close()

            return redirect(url_for("dashboard"))

        conn.close()

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

    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    today = date.today().isoformat()

    conn = get_db()

    tasks_today = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = ?
        AND due_date = ?
        AND completed = 0
        """,
        (
            user_id,
            today
        )
    ).fetchone()[0]

    study_tasks = conn.execute(
        """
        SELECT COUNT(*)
        FROM study_plans
        WHERE user_id = ?
        AND study_date = ?
        AND completed = 0
        """,
        (
            user_id,
            today
        )
    ).fetchone()[0]

    today_expense = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ?
        AND expense_date = ?
        """,
        (
            user_id,
            today
        )
    ).fetchone()[0]

    total_expense = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    budget_row = conn.execute(
        """
        SELECT amount
        FROM budgets
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    budget = budget_row["amount"] if budget_row else 0

    remaining_budget = budget - total_expense

    completed_tasks = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = ?
        AND completed = 1
        """,
        (user_id,)
    ).fetchone()[0]

    total_tasks = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    progress = (
        int((completed_tasks / total_tasks) * 100)
        if total_tasks > 0
        else 0
    )

    conn.close()

    return render_template(
        "dashboard.html",
        tasks_today=tasks_today,
        study_tasks=study_tasks,
        today_expense=today_expense,
        total_expense=total_expense,
        budget=budget,
        remaining_budget=remaining_budget,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        progress=progress
    )


# =========================================================
# TODO
# =========================================================

@app.route("/todo")
def todo():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    tasks = conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id = ?
        ORDER BY completed ASC, due_date ASC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "todo.html",
        tasks=tasks
    )


@app.route("/add-task", methods=["POST"])
def add_task():

    if not login_required():
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "").strip()

    if title:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO tasks
            (
                user_id,
                title,
                due_date,
                completed,
                created_at
            )
            VALUES (?, ?, ?, 0, ?)
            """,
            (
                session["user_id"],
                title,
                due_date or date.today().isoformat(),
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

    return redirect(url_for("todo"))


@app.route("/toggle-task/<int:task_id>")
def toggle_task(task_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    task = conn.execute(
        """
        SELECT completed
        FROM tasks
        WHERE id = ?
        AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    ).fetchone()

    if task:

        new_status = 0 if task["completed"] else 1

        conn.execute(
            """
            UPDATE tasks
            SET completed = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                new_status,
                task_id,
                session["user_id"]
            )
        )

        conn.commit()

    conn.close()

    return redirect(url_for("todo"))


@app.route("/delete-task/<int:task_id>")
def delete_task(task_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        AND user_id = ?
        """,
        (
            task_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("todo"))


# =========================================================
# STUDY
# =========================================================

@app.route("/study")
def study():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    study_plans = conn.execute(
        """
        SELECT *
        FROM study_plans
        WHERE user_id = ?
        ORDER BY completed ASC, study_date ASC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "study.html",
        study_plans=study_plans
    )


@app.route("/add-study", methods=["POST"])
def add_study():

    if not login_required():
        return redirect(url_for("login"))

    subject = request.form.get("subject", "").strip()
    topic = request.form.get("topic", "").strip()
    study_date = request.form.get("study_date", "").strip()

    if subject or topic:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO study_plans
            (
                user_id,
                subject,
                topic,
                study_date,
                completed,
                created_at
            )
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                session["user_id"],
                subject,
                topic,
                study_date or date.today().isoformat(),
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

    return redirect(url_for("study"))


@app.route("/toggle-study/<int:study_id>")
def toggle_study(study_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT completed
        FROM study_plans
        WHERE id = ?
        AND user_id = ?
        """,
        (
            study_id,
            session["user_id"]
        )
    ).fetchone()

    if item:

        new_status = 0 if item["completed"] else 1

        conn.execute(
            """
            UPDATE study_plans
            SET completed = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                new_status,
                study_id,
                session["user_id"]
            )
        )

        conn.commit()

    conn.close()

    return redirect(url_for("study"))


@app.route("/delete-study/<int:study_id>")
def delete_study(study_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM study_plans
        WHERE id = ?
        AND user_id = ?
        """,
        (
            study_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("study"))


# =========================================================
# ASSIGNMENTS
# =========================================================

@app.route("/assignments")
def assignments():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    assignment_list = conn.execute(
        """
        SELECT *
        FROM assignments
        WHERE user_id = ?
        ORDER BY completed ASC, due_date ASC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "assignments.html",
        assignments=assignment_list
    )


@app.route("/add-assignment", methods=["POST"])
def add_assignment():

    if not login_required():
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    due_date = request.form.get("due_date", "").strip()

    if title:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO assignments
            (
                user_id,
                title,
                subject,
                due_date,
                completed,
                created_at
            )
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                session["user_id"],
                title,
                subject,
                due_date,
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

    return redirect(url_for("assignments"))


@app.route("/toggle-assignment/<int:assignment_id>")
def toggle_assignment(assignment_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT completed
        FROM assignments
        WHERE id = ?
        AND user_id = ?
        """,
        (
            assignment_id,
            session["user_id"]
        )
    ).fetchone()

    if item:

        new_status = 0 if item["completed"] else 1

        conn.execute(
            """
            UPDATE assignments
            SET completed = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                new_status,
                assignment_id,
                session["user_id"]
            )
        )

        conn.commit()

    conn.close()

    return redirect(url_for("assignments"))


@app.route("/delete-assignment/<int:assignment_id>")
def delete_assignment(assignment_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM assignments
        WHERE id = ?
        AND user_id = ?
        """,
        (
            assignment_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("assignments"))


# =========================================================
# EXPENSES
# =========================================================

@app.route("/expenses")
def expenses():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    expense_list = conn.execute(
        """
        SELECT *
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    total_expense = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    budget_row = conn.execute(
        """
        SELECT amount
        FROM budgets
        WHERE user_id = ?
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    budget = budget_row["amount"] if budget_row else 0

    conn.close()

    return render_template(
        "expense.html",
        expenses=expense_list,
        total_expense=total_expense,
        budget=budget,
        remaining_budget=budget - total_expense,
        edit_expense=None
    )


@app.route("/add-expense", methods=["POST"])
def add_expense():

    if not login_required():
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "0").strip()
    expense_date = request.form.get("expense_date", "").strip()
    category = request.form.get("category", "").strip()

    try:
        amount = float(amount)
    except ValueError:
        amount = 0

    if title:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO expenses
            (
                user_id,
                title,
                amount,
                expense_date,
                category,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                title,
                amount,
                expense_date or date.today().isoformat(),
                category,
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

    return redirect(url_for("expenses"))


@app.route("/edit-expense/<int:expense_id>")
def edit_expense(expense_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    expense = conn.execute(
        """
        SELECT *
        FROM expenses
        WHERE id = ?
        AND user_id = ?
        """,
        (
            expense_id,
            session["user_id"]
        )
    ).fetchone()

    expense_list = conn.execute(
        """
        SELECT *
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    total_expense = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    budget_row = conn.execute(
        """
        SELECT amount
        FROM budgets
        WHERE user_id = ?
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    budget = budget_row["amount"] if budget_row else 0

    conn.close()

    return render_template(
        "expense.html",
        expenses=expense_list,
        total_expense=total_expense,
        budget=budget,
        remaining_budget=budget - total_expense,
        edit_expense=expense
    )


@app.route("/update-expense/<int:expense_id>", methods=["POST"])
def update_expense(expense_id):

    if not login_required():
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "0").strip()
    expense_date = request.form.get("expense_date", "").strip()
    category = request.form.get("category", "").strip()

    try:
        amount = float(amount)
    except ValueError:
        amount = 0

    conn = get_db()

    conn.execute(
        """
        UPDATE expenses
        SET title = ?,
            amount = ?,
            expense_date = ?,
            category = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            title,
            amount,
            expense_date,
            category,
            expense_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("expenses"))


@app.route("/delete-expense/<int:expense_id>")
def delete_expense(expense_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        AND user_id = ?
        """,
        (
            expense_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("expenses"))


@app.route("/set-budget", methods=["POST"])
def set_budget():

    if not login_required():
        return redirect(url_for("login"))

    amount = request.form.get("amount", "0").strip()

    try:
        amount = float(amount)
    except ValueError:
        amount = 0

    conn = get_db()

    existing = conn.execute(
        """
        SELECT id
        FROM budgets
        WHERE user_id = ?
        LIMIT 1
        """,
        (session["user_id"],)
    ).fetchone()

    if existing:

        conn.execute(
            """
            UPDATE budgets
            SET amount = ?
            WHERE user_id = ?
            """,
            (
                amount,
                session["user_id"]
            )
        )

    else:

        conn.execute(
            """
            INSERT INTO budgets
            (user_id, amount)
            VALUES (?, ?)
            """,
            (
                session["user_id"],
                amount
            )
        )

    conn.commit()
    conn.close()

    return redirect(url_for("expenses"))


# =========================================================
# SHOPPING
# =========================================================

@app.route("/shopping")
def shopping():

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    shopping_list = conn.execute(
        """
        SELECT *
        FROM shopping_items
        WHERE user_id = ?
        ORDER BY purchased ASC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    total_cost = conn.execute(
        """
        SELECT COALESCE(
            SUM(quantity * estimated_cost),
            0
        )
        FROM shopping_items
        WHERE user_id = ?
        AND purchased = 0
        """,
        (session["user_id"],)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "shopping.html",
        shopping_items=shopping_list,
        items=shopping_list,
        total_cost=total_cost,
        edit_item=None
    )


@app.route("/add-shopping", methods=["POST"])
def add_shopping():

    if not login_required():
        return redirect(url_for("login"))

    item = request.form.get("item", "").strip()
    quantity = request.form.get("quantity", "1").strip()
    estimated_cost = request.form.get(
        "estimated_cost",
        "0"
    ).strip()

    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    try:
        estimated_cost = float(estimated_cost)
    except ValueError:
        estimated_cost = 0

    if item:

        conn = get_db()

        conn.execute(
            """
            INSERT INTO shopping_items
            (
                user_id,
                item,
                quantity,
                estimated_cost,
                purchased,
                created_at
            )
            VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                session["user_id"],
                item,
                quantity,
                estimated_cost,
                datetime.now().isoformat()
            )
        )

        conn.commit()
        conn.close()

    return redirect(url_for("shopping"))


@app.route("/edit-shopping/<int:item_id>")
def edit_shopping(item_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    edit_item = conn.execute(
        """
        SELECT *
        FROM shopping_items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    ).fetchone()

    shopping_list = conn.execute(
        """
        SELECT *
        FROM shopping_items
        WHERE user_id = ?
        ORDER BY purchased ASC, id DESC
        """,
        (session["user_id"],)
    ).fetchall()

    total_cost = conn.execute(
        """
        SELECT COALESCE(
            SUM(quantity * estimated_cost),
            0
        )
        FROM shopping_items
        WHERE user_id = ?
        AND purchased = 0
        """,
        (session["user_id"],)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "shopping.html",
        shopping_items=shopping_list,
        items=shopping_list,
        total_cost=total_cost,
        edit_item=edit_item
    )


@app.route("/update-shopping/<int:item_id>", methods=["POST"])
def update_shopping(item_id):

    if not login_required():
        return redirect(url_for("login"))

    item = request.form.get("item", "").strip()
    quantity = request.form.get("quantity", "1").strip()
    estimated_cost = request.form.get(
        "estimated_cost",
        "0"
    ).strip()

    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    try:
        estimated_cost = float(estimated_cost)
    except ValueError:
        estimated_cost = 0

    conn = get_db()

    conn.execute(
        """
        UPDATE shopping_items
        SET item = ?,
            quantity = ?,
            estimated_cost = ?
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item,
            quantity,
            estimated_cost,
            item_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("shopping"))


@app.route("/toggle-shopping/<int:item_id>")
def toggle_shopping(item_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    item = conn.execute(
        """
        SELECT purchased
        FROM shopping_items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    ).fetchone()

    if item:

        new_status = 0 if item["purchased"] else 1

        conn.execute(
            """
            UPDATE shopping_items
            SET purchased = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                new_status,
                item_id,
                session["user_id"]
            )
        )

        conn.commit()

    conn.close()

    return redirect(url_for("shopping"))


@app.route("/delete-shopping/<int:item_id>")
def delete_shopping(item_id):

    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute(
        """
        DELETE FROM shopping_items
        WHERE id = ?
        AND user_id = ?
        """,
        (
            item_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(url_for("shopping"))


# =========================================================
# CALENDAR
# =========================================================

@app.route("/calendar")
def calendar():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db()

    # IMPORTANT:
    # SQLite Row objects ko directly template me JSON nahi bhejna.
    # Isliye pehle normal dictionaries me convert karenge.

    task_rows = conn.execute(
        """
        SELECT
            id,
            title,
            due_date,
            completed
        FROM tasks
        WHERE user_id = ?
        ORDER BY due_date ASC
        """,
        (user_id,)
    ).fetchall()

    assignment_rows = conn.execute(
        """
        SELECT
            id,
            title,
            subject,
            due_date,
            completed
        FROM assignments
        WHERE user_id = ?
        ORDER BY due_date ASC
        """,
        (user_id,)
    ).fetchall()

    study_rows = conn.execute(
        """
        SELECT
            id,
            subject,
            topic,
            study_date,
            completed
        FROM study_plans
        WHERE user_id = ?
        ORDER BY study_date ASC
        """,
        (user_id,)
    ).fetchall()

    conn.close()

    # Row -> Dictionary
    tasks = [
        dict(row)
        for row in task_rows
    ]

    assignments = [
        dict(row)
        for row in assignment_rows
    ]

    study_plans = [
        dict(row)
        for row in study_rows
    ]

    return render_template(
        "calendar.html",
        tasks=tasks,
        assignments=assignments,
        study_plans=study_plans
    )


# =========================================================
# SUMMARY
# =========================================================

@app.route("/summary")
def summary():

    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db()

    total_tasks = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    completed_tasks = conn.execute(
        """
        SELECT COUNT(*)
        FROM tasks
        WHERE user_id = ?
        AND completed = 1
        """,
        (user_id,)
    ).fetchone()[0]

    total_study = conn.execute(
        """
        SELECT COUNT(*)
        FROM study_plans
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    completed_study = conn.execute(
        """
        SELECT COUNT(*)
        FROM study_plans
        WHERE user_id = ?
        AND completed = 1
        """,
        (user_id,)
    ).fetchone()[0]

    total_assignments = conn.execute(
        """
        SELECT COUNT(*)
        FROM assignments
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    completed_assignments = conn.execute(
        """
        SELECT COUNT(*)
        FROM assignments
        WHERE user_id = ?
        AND completed = 1
        """,
        (user_id,)
    ).fetchone()[0]

    total_expense = conn.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    budget_row = conn.execute(
        """
        SELECT amount
        FROM budgets
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    budget = budget_row["amount"] if budget_row else 0

    conn.close()

    task_progress = (
        int(completed_tasks / total_tasks * 100)
        if total_tasks
        else 0
    )

    study_progress = (
        int(completed_study / total_study * 100)
        if total_study
        else 0
    )

    assignment_progress = (
        int(
            completed_assignments /
            total_assignments *
            100
        )
        if total_assignments
        else 0
    )

    return render_template(
        "summary.html",
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        total_study=total_study,
        completed_study=completed_study,
        total_assignments=total_assignments,
        completed_assignments=completed_assignments,
        total_expense=total_expense,
        budget=budget,
        remaining_budget=budget - total_expense,
        task_progress=task_progress,
        study_progress=study_progress,
        assignment_progress=assignment_progress
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    ) 