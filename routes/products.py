
from flask import Blueprint, render_template, abort
from db import get_db_connection

products = Blueprint("products", __name__)

@products.route("/shop")
def shop():
    connection = get_db_connection()
    pcs = []

    if connection:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT pc_ID, model_name, price, specs, type
            FROM PC
            WHERE order_ID IS NULL
        """)

        pcs = cursor.fetchall()

        cursor.close()
        connection.close()

    return render_template("shop.html", pcs=pcs)


@products.route("/shop/<int:pc_id>")
def pc_details(pc_id):
    connection = get_db_connection()

    if connection is None:
        return "<h1>Database connection failed!</h1>"

    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT pc_ID, model_name, price, specs, type,
               promo_text, description, image, order_ID
        FROM PC
        WHERE pc_ID = %s
    """, (pc_id,))

    pc = cursor.fetchone()

    cursor.close()
    connection.close()

    if pc is None:
        abort(404)

    return render_template("pc_details.html", pc=pc)
