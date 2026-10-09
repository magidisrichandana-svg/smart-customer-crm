from flask import (
    Flask, render_template, request,
    redirect, url_for, make_response, flash
)
import sqlite3
import csv
import os
from io import StringIO

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-only-change-me"
)

# ==============================
# DATABASE CONNECTION & INIT
# ==============================
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company_name TEXT,
            prospect_status TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT,
            country TEXT,
            income_source TEXT,
            tags TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize table on start
init_db()


# ==============================
# DASHBOARD
# ==============================
@app.route("/")
def dashboard():
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM customers")
        total = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT prospect_status, COUNT(*) AS count
            FROM customers
            GROUP BY prospect_status
        """)
        status_counts = cursor.fetchall()

        cursor.execute("""
            SELECT * FROM customers
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_customers = cursor.fetchall()

        return render_template(
            "dashboard.html",
            total=total,
            status_counts=status_counts,
            recent_customers=recent_customers
        )
    finally:
        db.close()


# ==============================
# CUSTOMER LIST AND SEARCH
# ==============================
@app.route("/customers")
def customers():
    search = request.args.get("search", "").strip()

    db = get_db_connection()
    cursor = db.cursor()

    try:
        if search:
            value = f"%{search}%"
            cursor.execute("""
                SELECT * FROM customers
                WHERE name LIKE ?
                   OR company_name LIKE ?
                   OR phone LIKE ?
                   OR email LIKE ?
                   OR tags LIKE ?
                ORDER BY id DESC
            """, (value, value, value, value, value))
        else:
            cursor.execute("SELECT * FROM customers ORDER BY id DESC")

        customer_list = cursor.fetchall()

        return render_template(
            "customers.html",
            customers=customer_list,
            search=search
        )
    finally:
        db.close()


# ==============================
# ADD CUSTOMER
# ==============================
@app.route("/add", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        company_name = request.form.get("company_name", "").strip()
        prospect_status = request.form.get("prospect_status", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        country = request.form.get("country", "").strip()
        income_source = request.form.get("income_source", "").strip()
        tags = request.form.get("tags", "").strip()
        notes = request.form.get("notes", "").strip()

        if not name:
            flash("Customer name is required.")
            return redirect(url_for("add_customer"))

        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor.execute("""
                INSERT INTO customers (
                    name, company_name, prospect_status,
                    phone, email, address, city, country,
                    income_source, tags, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, company_name, prospect_status,
                phone, email, address, city, country,
                income_source, tags, notes
            ))

            db.commit()
            flash("Customer added successfully!")

        except sqlite3.Error:
            db.rollback()
            flash("Could not add customer. Please check the database.")

        finally:
            db.close()

        return redirect(url_for("customers"))

    return render_template("add_customer.html")


# ==============================
# VIEW CUSTOMER
# ==============================
@app.route("/view/<int:id>")
def view_customer(id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT * FROM customers WHERE id = ?", (id,))
        customer = cursor.fetchone()

        if customer is None:
            return "Customer not found", 404

        return render_template(
            "view_customer.html",
            customer=customer
        )
    finally:
        db.close()


# ==============================
# EDIT CUSTOMER
# ==============================
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_customer(id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT * FROM customers WHERE id = ?", (id,))
        customer = cursor.fetchone()

        if customer is None:
            return "Customer not found", 404

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            company_name = request.form.get("company_name", "").strip()
            prospect_status = request.form.get("prospect_status", "").strip()
            phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip()
            address = request.form.get("address", "").strip()
            city = request.form.get("city", "").strip()
            country = request.form.get("country", "").strip()
            income_source = request.form.get("income_source", "").strip()
            tags = request.form.get("tags", "").strip()
            notes = request.form.get("notes", "").strip()

            if not name:
                flash("Customer name is required.")
                return redirect(url_for("edit_customer", id=id))

            cursor.execute("""
                UPDATE customers
                SET name = ?,
                    company_name = ?,
                    prospect_status = ?,
                    phone = ?,
                    email = ?,
                    address = ?,
                    city = ?,
                    country = ?,
                    income_source = ?,
                    tags = ?,
                    notes = ?
                WHERE id = ?
            """, (
                name, company_name, prospect_status,
                phone, email, address, city, country,
                income_source, tags, notes, id
            ))

            db.commit()
            flash("Customer updated successfully!")
            return redirect(url_for("customers"))

        return render_template(
            "edit_customer.html",
            customer=customer
        )
    finally:
        db.close()


# ==============================
# DELETE CUSTOMER
# ==============================
@app.route("/delete/<int:id>", methods=["POST"])
def delete_customer(id):
    db = get_db_connection()

    try:
        db.execute("DELETE FROM customers WHERE id = ?", (id,))
        db.commit()
        flash("Customer deleted successfully!")

    except sqlite3.Error:
        db.rollback()
        flash("Could not delete customer.")

    finally:
        db.close()

    return redirect(url_for("customers"))


# ==============================
# EXPORT CUSTOMERS TO CSV
# ==============================
@app.route("/export")
def export_customers():
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT id, name, company_name, prospect_status,
                   phone, email, address, city, country,
                   income_source, tags, notes, created_at
            FROM customers
            ORDER BY id DESC
        """)
        customer_list = cursor.fetchall()
    finally:
        db.close()

    output = StringIO()
    output.write("\ufeff")

    columns = [
        "id", "name", "company_name", "prospect_status",
        "phone", "email", "address", "city", "country",
        "income_source", "tags", "notes", "created_at"
    ]

    writer = csv.writer(output)
    writer.writerow(columns)

    for customer in customer_list:
        writer.writerow([
            customer[column] for column in columns
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=customers.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"

    return response


if __name__ == "__main__":
    app.run(debug=True)
