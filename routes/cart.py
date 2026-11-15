
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, session, abort
from db import get_db_connection

cart = Blueprint("cart", __name__)

PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal"]


def get_cart_pcs(cursor):
    """Return the unsold PCs in the session cart, in the order they were added."""
    cart_ids = session.get("cart", [])

    if not cart_ids:
        return []

    placeholders = ", ".join(["%s"] * len(cart_ids))

    cursor.execute(f"""
        SELECT pc_ID, model_name, price, specs, image
        FROM PC
        WHERE pc_ID IN ({placeholders}) AND order_ID IS NULL
    """, tuple(cart_ids))

    pcs = cursor.fetchall()
    pcs.sort(key=lambda pc: cart_ids.index(pc["pc_ID"]))

    # Drop any PCs that were sold since they were added
    session["cart"] = [pc["pc_ID"] for pc in pcs]

    return pcs


@cart.route("/cart")
def view_cart():
    pcs = []

    if session.get("cart"):
        connection = get_db_connection()

        if connection is None:
            return "<h1>Database connection failed!</h1>"

        cursor = connection.cursor(dictionary=True)
        pcs = get_cart_pcs(cursor)

        cursor.close()
        connection.close()

    subtotal = sum(pc["price"] for pc in pcs)

    return render_template("cart.html", pcs=pcs, subtotal=subtotal)


@cart.route("/cart/add/<int:pc_id>", methods=["POST"])
def add_to_cart(pc_id):
    cart_ids = session.get("cart", [])

    if pc_id not in cart_ids:
        session["cart"] = cart_ids + [pc_id]

    return redirect(url_for("cart.view_cart"))


@cart.route("/cart/remove/<int:pc_id>", methods=["POST"])
def remove_from_cart(pc_id):
    cart_ids = session.get("cart", [])

    session["cart"] = [i for i in cart_ids if i != pc_id]

    return redirect(url_for("cart.view_cart"))


@cart.route("/checkout", methods=["GET", "POST"])
def checkout():

    if "customer_id" not in session:
        return redirect(url_for("customers.login", next=url_for("cart.checkout")))

    connection = get_db_connection()

    if connection is None:
        return "<h1>Database connection failed!</h1>"

    cursor = connection.cursor(dictionary=True)
    pcs = get_cart_pcs(cursor)

    if not pcs:
        cursor.close()
        connection.close()
        return redirect(url_for("cart.view_cart"))

    total = sum(pc["price"] for pc in pcs)
    error = None

    if request.method == "POST":

        payment_method = request.form.get("payment_method", "")

        if payment_method not in PAYMENT_METHODS:
            error = "Please choose a payment method."

        else:
            cursor.execute("""
                INSERT INTO Orders
                (order_date, total_price, payment_method, customer_ID)
                VALUES (%s, %s, %s, %s)
            """, (
                date.today(),
                total,
                payment_method,
                session["customer_id"]
            ))

            order_id = cursor.lastrowid
            pc_ids = [pc["pc_ID"] for pc in pcs]
            placeholders = ", ".join(["%s"] * len(pc_ids))

            # Only claim PCs that are still unsold
            cursor.execute(f"""
                UPDATE PC
                SET order_ID = %s
                WHERE pc_ID IN ({placeholders}) AND order_ID IS NULL
            """, (order_id, *pc_ids))

            if cursor.rowcount != len(pc_ids):
                connection.rollback()
                error = "Some items in your cart were just sold. Please review your cart."

            else:
                connection.commit()
                session["cart"] = []

                cursor.close()
                connection.close()

                return redirect(url_for("cart.order_confirmation", order_id=order_id))

    cursor.close()
    connection.close()

    return render_template(
        "checkout.html",
        pcs=pcs,
        total=total,
        payment_methods=PAYMENT_METHODS,
        error=error
    )


@cart.route("/orders/<int:order_id>")
def order_confirmation(order_id):

    if "customer_id" not in session:
        return redirect(url_for("customers.login"))

    connection = get_db_connection()

    if connection is None:
        return "<h1>Database connection failed!</h1>"

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT order_ID, order_date, total_price, payment_method
        FROM Orders
        WHERE order_ID = %s AND customer_ID = %s
    """, (order_id, session["customer_id"]))

    order = cursor.fetchone()

    if order is None:
        cursor.close()
        connection.close()
        abort(404)

    cursor.execute("""
        SELECT pc_ID, model_name, price, specs, image
        FROM PC
        WHERE order_ID = %s
    """, (order_id,))

    pcs = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template("order_confirmation.html", order=order, pcs=pcs)
