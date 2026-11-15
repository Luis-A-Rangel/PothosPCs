
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db_connection

customers = Blueprint("customers", __name__)


@customers.route("/register", methods=["GET", "POST"])
def register():

    error = None
    success = None

    if request.method == "POST":

        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not all([first_name, last_name, email, phone, password]):
            error = "Please fill in all fields."

        else:
            connection = get_db_connection()

            if connection is None:
                error = "Could not connect to the database."

            else:
                cursor = connection.cursor(dictionary=True)

                cursor.execute(
                    "SELECT customer_ID FROM Customer WHERE email = %s",
                    (email,)
                )

                existing_customer = cursor.fetchone()

                if existing_customer:
                    error = "An account with that email already exists."

                else:
                    hashed_password = generate_password_hash(password)

                    cursor.execute("""
                        INSERT INTO Customer
                        (email, password, first_Name, last_Name, phone)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        email,
                        hashed_password,
                        first_name,
                        last_name,
                        phone
                    ))

                    connection.commit()

                    session["customer_id"] = cursor.lastrowid
                    session["customer_name"] = first_name
                    success = "Your account was created successfully!"

                cursor.close()
                connection.close()

                if success:
                    return redirect(url_for("main.home"))

    return render_template(
        "register.html",
        error=error,
        success=success
    )


@customers.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db_connection()

        if connection is None:
            error = "Could not connect to the database."

        else:
            cursor = connection.cursor(dictionary=True)

            cursor.execute("""
                SELECT customer_ID, first_Name, last_Name, password
                FROM Customer
                WHERE email = %s
            """, (email,))

            customer = cursor.fetchone()

            cursor.close()
            connection.close()

            if customer and check_password_hash(customer["password"], password):

                session["customer_id"] = customer["customer_ID"]
                session["customer_name"] = customer["first_Name"]

                # Send the customer back to where they were (e.g. checkout)
                next_page = request.args.get("next", "")

                if next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)

                return redirect(url_for("main.home"))

            else:
                error = "Invalid email or password."

    return render_template("login.html", error=error)


@customers.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("main.home"))

